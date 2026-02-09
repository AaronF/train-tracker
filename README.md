# Train Tracker

## What This Project Does

This project has 2 runtime parts:

1. `watch_trains.py` (backend worker)
- Connects to Network Rail STOMP feed (`/topic/TD_ALL_SIG_AREA`)
- Converts signal movements into segment occupancy data using `segment_maker.py`
- Publishes segment updates to MQTT

2. `app.py` (web server)
- Serves the UI from `web/` on port `1234`
- `web/index.html` + `web/assets/dist/js/main.js` connect to MQTT over WebSocket and render the 4 lines

## Setup

1. `cd ~/your-project-folder`
2. `python3 -m venv venv`
3. `source venv/bin/activate`
4. `pip3 install -r requirements.txt`

## Configuration

### 1) Backend environment (`.env`)

Copy `.env.sample` to `.env` and set:

- `NETWORK_RAIL_USERNAME`
- `NETWORK_RAIL_PASSWORD`
- `MQTT_HOST`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`
- Optional: `MQTT_PORT` (defaults to `1883`)

### 2) Frontend MQTT config (`web/assets/config.js`)

Set:

- `host`
- `port` (WebSocket listener port)
- `username`
- `password`
- `secure` (`true` for `wss`, `false` for `ws`)

## Run

Use 2 terminals.

### Terminal 1: backend worker

```bash
source venv/bin/activate
python3 watch_trains.py
```

### Terminal 2: web server

```bash
source venv/bin/activate
python3 app.py
```

Open:

- `http://localhost:1234`

## Notes / Gotchas

- The UI currently subscribes to MQTT topic `trains/segments` in `web/assets/dist/js/main.js`.
- `watch_trains.py` publishes a full-state snapshot to `trains/segments` every 5 seconds.
- The UI and backend topics now match by default.

## Troubleshooting

- Check runtime logs in `connection.log`.
- If STOMP cannot connect to `publicdatafeeds.networkrail.co.uk:61618`, live train data will not flow even if MQTT and the web UI are running.
