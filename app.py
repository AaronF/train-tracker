from flask import Flask, send_from_directory
from pathlib import Path

app = Flask(__name__, static_folder=None)
WEB_DIR = Path(__file__).parent / "web"

@app.route("/")
def index():
	return send_from_directory(WEB_DIR, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
	return send_from_directory(WEB_DIR, path)

if __name__ == "__main__":
	# Bind to all interfaces for LAN access
	app.run(host="0.0.0.0", port=1234)