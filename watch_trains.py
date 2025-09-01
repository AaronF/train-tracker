#!/usr/bin/env python3
import os
import time
import json
import datetime
import logging
from dotenv import load_dotenv

import stomp
import paho.mqtt.client as mqtt

import segment_maker

load_dotenv()

# ====== Config ======
HOST = 'publicdatafeeds.networkrail.co.uk'
PORT = 61618
DESTINATION = '/topic/TD_ALL_SIG_AREA'

AREA = ['KG', 'WG']
HEARTBEATS_MS = (15000, 15000)

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USERNAME')
MQTT_PASS = os.getenv('MQTT_PASSWORD')
MQTT_TOPIC = 'trains/segments'
MQTT_TOPIC_BASE = 'trains/segments'

# Backoff settings for MQTT connect attempts
MQTT_BACKOFF_START = 1       # seconds
MQTT_BACKOFF_MAX = 60        # seconds
# =====================

logging.basicConfig(
	filename='connection.log',
	encoding='utf-8',
	filemode='a',
	level=logging.INFO,
	format='[%(asctime)s] %(levelname)s: %(message)s',
)

SEGMENTS = segment_maker.make_segments()

# ---------------- MQTT helpers ----------------
def make_mqtt_client():
	"""Create an MQTT client with callbacks; doesn't connect yet."""
	client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
	if MQTT_USER and MQTT_PASS:
		client.username_pw_set(MQTT_USER, MQTT_PASS)

	# state used for backoff between attempts
	state = {
		"next_delay": MQTT_BACKOFF_START,
		"next_try_at": 0.0,
		"ever_connected": False
	}
	client.user_data_set(state)

	def on_connect(c, userdata, flags, reason_code, properties=None):
		if reason_code == 0:
			logging.info('MQTT connected to %s:%s', MQTT_HOST, MQTT_PORT)
			userdata["ever_connected"] = True
			userdata["next_delay"] = MQTT_BACKOFF_START  # reset backoff on success
		else:
			logging.error('MQTT connect failed (rc=%s)', reason_code)

	def on_disconnect(c, userdata, reason_code, properties=None):
		# Non-zero means unexpected disconnect; paho will try to reconnect,
		# but we also allow manual ensure() attempts.
		if reason_code != 0:
			logging.warning('MQTT disconnected (rc=%s); will retry', reason_code)

	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.loop_start()
	return client

def ensure_mqtt_connected(client):
	"""
	Attempt to connect if not connected, with capped exponential backoff.
	Never raises; only logs.
	"""
	if not MQTT_HOST:
		return  # no host configured; silently do nothing

	state = client.user_data_get() or {}
	now = time.time()

	# Already connected? nothing to do
	if client.is_connected():
		return

	# Respect backoff schedule
	if now < state.get("next_try_at", 0):
		return

	try:
		logging.info('MQTT connecting to %s:%s …', MQTT_HOST, MQTT_PORT)
		# connect() may raise (DNS failure, refused, etc.) — catch below
		client.connect(MQTT_HOST, MQTT_PORT, keepalive=20)
		# If connect() doesn't raise, paho will finish handshake in background.
		# We'll know success via on_connect, and client.is_connected() soon after.
	except Exception as e:
		logging.error('MQTT connect attempt failed: %s', e)
		# schedule next try with increased delay
		delay = min(state.get("next_delay", MQTT_BACKOFF_START) * 2, MQTT_BACKOFF_MAX)
		state["next_delay"] = delay
		state["next_try_at"] = now + delay
		return

	# connect() call succeeded (no exception). Schedule a short grace window
	# before we try again if it's still not connected.
	state["next_delay"] = min(state.get("next_delay", MQTT_BACKOFF_START), MQTT_BACKOFF_START)
	state["next_try_at"] = now + 3  # give the async handshake a couple seconds
# -------------- end MQTT helpers --------------


def to_segment(action: dict) -> None:
	train = action.get('descr')
	if not train:
		return

	if 'to' in action:
		signal = action['to']
		current_segment = next(((n, s) for n, s in SEGMENTS.items() if train in s['trains']), None)
		target_segment = next(((n, s) for n, s in SEGMENTS.items() if signal in s['signals']), None)

		if current_segment:
			current_segment[1]['trains'].remove(train)
		if target_segment:
			target_segment[1]['trains'].clear()
			target_segment[1]['trains'].append(train)
		return

	if 'from' in action:
		for segment in SEGMENTS.values():
			if train in segment['trains']:
				segment['trains'].remove(train)
				break


def print_segments() -> None:
	current_line = ""
	for seg_name, seg in SEGMENTS.items():
		if current_line != seg['name']:
			print("\n", seg['name'])
			current_line = seg['name']
		if not seg['trains']:
			print("__", end="")
		else:
			print(seg['trains'], end="")
	print("\n")

def build_line_payloads(segments: dict) -> dict:
	"""
	Returns:
	  {
		'line_1': { 'SEG00': {...}, 'SEG01': {...}, ... },
		'line_2': { ... },
		'line_3': { ... },
		'line_4': { ... },
	  }
	Only segments with a valid 'name' are included.
	"""
	lines = {'line_1': {}, 'line_2': {}, 'line_3': {}, 'line_4': {}}
	for seg_id, seg in segments.items():
		line = seg.get('name')
		if line in lines:
			# Minimal payload the browser expects (value.trains), or send full seg if you prefer
			# minimal:
			lines[line][seg_id] = {'trains': seg.get('trains', [])}
			# full:
			# lines[line][seg_id] = seg
	return lines

class Listener(stomp.ConnectionListener):
	def __init__(self, conn: stomp.Connection, destination: str):
		self.conn = conn
		self.destination = destination

	def on_connected(self, frame):
		logging.info('STOMP connected; subscribing to %s', self.destination)
		self.conn.subscribe(destination=self.destination, id='td', ack='auto')

	def on_message(self, frame):
		try:
			data = json.loads(frame.body)
		except json.JSONDecodeError:
			logging.warning('Bad JSON payload; skipping')
			return

		if not isinstance(data, list):
			return

		for item in data:
			if not isinstance(item, dict):
				continue
			for key, value in item.items():
				if key in ('CA_MSG', 'CB_MSG', 'CC_MSG', 'CT_MSG'):
					if isinstance(value, dict) and value.get('area_id') in AREA:
						for _, action in item.items():
							if isinstance(action, dict):
								to_segment(action)

	def on_error(self, frame):
		logging.error('STOMP error: %s', getattr(frame, 'body', frame))

	def on_disconnected(self):
		logging.warning('STOMP disconnected')


def connect_stomp_with_retry(conn: stomp.Connection):
	delay = 1
	while not conn.is_connected():
		try:
			logging.info('Connecting STOMP to %s:%s …', HOST, PORT)
			conn.connect(
				os.getenv('NETWORK_RAIL_USERNAME'),
				os.getenv('NETWORK_RAIL_PASSWORD'),
				wait=True
			)
			if conn.is_connected():
				logging.info('STOMP connected')
				return
		except Exception as e:
			logging.error('STOMP connect failed: %s', e)
		time.sleep(delay)
		delay = min(delay * 2, 60)


def main():
	# Init MQTT (no crash if unreachable)
	mqttc = make_mqtt_client()
	ensure_mqtt_connected(mqttc)  # first attempt (non-fatal if it fails)

	# STOMP
	conn = stomp.Connection([(HOST, PORT)], heartbeats=HEARTBEATS_MS)
	conn.set_listener('', Listener(conn, DESTINATION))
	connect_stomp_with_retry(conn)

	line_payloads = build_line_payloads(SEGMENTS)

	try:
		while True:
			# Keep STOMP alive/reconnect if needed
			if not conn.is_connected():
				logging.warning('Detected STOMP disconnect; reconnecting…')
				connect_stomp_with_retry(conn)

			# Keep trying MQTT in the background without crashing
			ensure_mqtt_connected(mqttc)

			# Your periodic work
			print("\n//// TRAINS ////", datetime.datetime.now().strftime("%H:%M:%S"))
			print_segments()

			# Only publish if connected; otherwise skip quietly
			if mqttc.is_connected():
				try:
					# mqttc.publish(MQTT_TOPIC, json.dumps(SEGMENTS), qos=0, retain=False)

					for line_name, payload in line_payloads.items():
						if not payload:
							# Optional: skip empty payloads to reduce noise
							continue
						topic = f'{MQTT_TOPIC_BASE}/{line_name}'
						try:
							mqttc.publish(topic, json.dumps(payload), qos=0, retain=False)
						except Exception as e:
							logging.error('MQTT publish to %s failed: %s', topic, e)
				except Exception as e:
					logging.error('MQTT publish failed: %s', e)
			else:
				logging.debug('MQTT not connected; skipping publish')

			time.sleep(5)
	except KeyboardInterrupt:
		logging.info('Shutting down…')
	finally:
		try:
			conn.disconnect()
		except Exception:
			pass
		try:
			mqttc.loop_stop()
			mqttc.disconnect()
		except Exception:
			pass


if __name__ == '__main__':
	main()