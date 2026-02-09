#!/usr/bin/env python3
import datetime
import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

import paho.mqtt.client as mqtt
import stomp

import segment_maker

load_dotenv()

# ====== Config ======
HOST = "publicdatafeeds.networkrail.co.uk"
PORT = 61618
DESTINATION = "/topic/TD_ALL_SIG_AREA"

AREA = ["KG", "WG"]
HEARTBEATS_MS = (15000, 15000)

NETWORK_RAIL_USERNAME = os.getenv("NETWORK_RAIL_USERNAME")
NETWORK_RAIL_PASSWORD = os.getenv("NETWORK_RAIL_PASSWORD")

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USERNAME")
MQTT_PASS = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = "trains/segments"
MQTT_TOPIC_BASE = "trains/segments"

RETRY_BACKOFF_START = 1
RETRY_BACKOFF_MAX = 60
PUBLISH_INTERVAL_SECONDS = 5
# =====================

logging.basicConfig(
    filename="connection.log",
    encoding="utf-8",
    filemode="a",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
)

SEGMENTS = segment_maker.make_segments()
TD_MESSAGE_TYPES = ("CA_MSG", "CB_MSG", "CC_MSG", "CT_MSG")


def new_retry_state() -> dict[str, Any]:
    return {
        "next_try_at": 0.0,
        "delay": RETRY_BACKOFF_START,
        "ever_connected": False,
    }


def schedule_retry(retry_state: dict[str, Any], now: float, event_name: str) -> None:
    delay = retry_state["delay"]
    retry_state["next_try_at"] = now + delay
    retry_state["delay"] = min(delay * 2, RETRY_BACKOFF_MAX)
    logging.info("%s delay=%ss", event_name, delay)


def reset_retry(retry_state: dict[str, Any]) -> None:
    retry_state["next_try_at"] = 0.0
    retry_state["delay"] = RETRY_BACKOFF_START


# Segment state
def to_segment(action: dict[str, Any], segments: dict[str, Any]) -> None:
    train = action.get("descr")
    if not train:
        return

    if "to" in action:
        signal = action["to"]
        current_segment = next(
            ((name, seg) for name, seg in segments.items() if train in seg["trains"]),
            None,
        )
        target_segment = next(
            ((name, seg) for name, seg in segments.items() if signal in seg["signals"]),
            None,
        )

        if current_segment:
            current_segment[1]["trains"].remove(train)
        if target_segment:
            target_segment[1]["trains"].clear()
            target_segment[1]["trains"].append(train)
        return

    if "from" in action:
        for segment in segments.values():
            if train in segment["trains"]:
                segment["trains"].remove(train)
                break


def extract_actions_from_td_batch(data: Any) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return actions

    for item in data:
        if not isinstance(item, dict):
            continue

        should_apply = False
        for key, value in item.items():
            if key in TD_MESSAGE_TYPES and isinstance(value, dict) and value.get("area_id") in AREA:
                should_apply = True
                break

        if not should_apply:
            continue

        for action in item.values():
            if isinstance(action, dict):
                actions.append(action)

    return actions


def build_segments_payload(segments: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for seg_id, seg in segments.items():
        payload[seg_id] = {"trains": list(seg.get("trains", []))}
    return payload


def build_line_payloads(segments: dict[str, Any]) -> dict[str, dict[str, Any]]:
    line_payloads: dict[str, dict[str, Any]] = {
        "line_1": {},
        "line_2": {},
        "line_3": {},
        "line_4": {},
    }
    for seg_id, seg in segments.items():
        line = seg.get("name")
        if line in line_payloads:
            line_payloads[line][seg_id] = {"trains": list(seg.get("trains", []))}
    return line_payloads


def print_segments(segments: dict[str, Any]) -> None:
    current_line = ""
    for _, seg in segments.items():
        if current_line != seg["name"]:
            print("\n", seg["name"])
            current_line = seg["name"]
        if not seg["trains"]:
            print("__", end="")
        else:
            print(seg["trains"], end="")
    print("\n")


# STOMP runtime
class Listener(stomp.ConnectionListener):
    def __init__(self, conn: stomp.Connection, destination: str, segments: dict[str, Any]):
        self.conn = conn
        self.destination = destination
        self.segments = segments

    def on_connected(self, frame: Any) -> None:
        logging.info("stomp_connected destination=%s", self.destination)
        self.conn.subscribe(destination=self.destination, id="td", ack="auto")

    def on_message(self, frame: Any) -> None:
        try:
            data = json.loads(frame.body)
        except json.JSONDecodeError:
            logging.warning("stomp_bad_json")
            return

        for action in extract_actions_from_td_batch(data):
            to_segment(action, self.segments)

    def on_error(self, frame: Any) -> None:
        logging.error("stomp_error body=%s", getattr(frame, "body", frame))

    def on_disconnected(self) -> None:
        logging.warning("stomp_disconnected")


def ensure_stomp_connection(conn: stomp.Connection, retry_state: dict[str, Any]) -> None:
    if conn.is_connected():
        return

    now = time.time()
    if now < retry_state["next_try_at"]:
        return

    try:
        logging.info("stomp_connect_attempt host=%s port=%s", HOST, PORT)
        conn.connect(NETWORK_RAIL_USERNAME, NETWORK_RAIL_PASSWORD, wait=True)
        if conn.is_connected():
            retry_state["ever_connected"] = True
            reset_retry(retry_state)
            logging.info("stomp_connected host=%s port=%s", HOST, PORT)
            return
        schedule_retry(retry_state, now, "stomp_reconnect_scheduled")
    except Exception as exc:
        logging.error("stomp_connect_failed error=%s", exc)
        schedule_retry(retry_state, now, "stomp_reconnect_scheduled")


# MQTT runtime
def make_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(_client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: int, _properties: Any = None) -> None:
        if reason_code == 0:
            logging.info("mqtt_connected host=%s port=%s", MQTT_HOST, MQTT_PORT)
        else:
            logging.error("mqtt_connect_failed reason_code=%s", reason_code)

    def on_disconnect(_client: mqtt.Client, _userdata: Any, reason_code: int, _properties: Any = None) -> None:
        if reason_code != 0:
            logging.warning("mqtt_disconnected reason_code=%s", reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.loop_start()
    return client


def ensure_mqtt_connection(client: mqtt.Client, retry_state: dict[str, Any]) -> None:
    if not MQTT_HOST:
        return

    if client.is_connected():
        return

    now = time.time()
    if now < retry_state["next_try_at"]:
        return

    try:
        if retry_state["ever_connected"]:
            logging.info("mqtt_connect_attempt mode=reconnect host=%s port=%s", MQTT_HOST, MQTT_PORT)
            client.reconnect()
        else:
            logging.info("mqtt_connect_attempt mode=initial host=%s port=%s", MQTT_HOST, MQTT_PORT)
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=20)

        retry_state["ever_connected"] = True
        reset_retry(retry_state)
    except Exception as exc:
        logging.error("mqtt_connect_failed error=%s", exc)
        schedule_retry(retry_state, now, "mqtt_reconnect_scheduled")


def publish_snapshot(client: mqtt.Client, segments: dict[str, Any]) -> None:
    for line_name, payload in build_line_payloads(segments).items():
        topic = f"{MQTT_TOPIC_BASE}/{line_name}"
        client.publish(topic, json.dumps(payload), qos=0, retain=False)


# Main loop
def main() -> None:
    mqtt_client = make_mqtt_client()
    mqtt_retry = new_retry_state()

    stomp_conn = stomp.Connection([(HOST, PORT)], heartbeats=HEARTBEATS_MS)
    stomp_conn.set_listener("", Listener(stomp_conn, DESTINATION, SEGMENTS))
    stomp_retry = new_retry_state()

    try:
        while True:
            ensure_stomp_connection(stomp_conn, stomp_retry)
            ensure_mqtt_connection(mqtt_client, mqtt_retry)

            print("\n//// TRAINS ////", datetime.datetime.now().strftime("%H:%M:%S"))
            print_segments(SEGMENTS)

            if mqtt_client.is_connected():
                try:
                    publish_snapshot(mqtt_client, SEGMENTS)
                except Exception as exc:
                    logging.error("mqtt_publish_failed error=%s", exc)
            else:
                logging.debug("mqtt_not_connected skipping_publish")

            time.sleep(PUBLISH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("shutdown_requested")
    finally:
        try:
            stomp_conn.disconnect()
        except Exception:
            pass

        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
