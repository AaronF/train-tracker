from flask import Flask
from pathlib import Path

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"

# Serve files from /web at the root URL path
app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/")

@app.get("/")
def home():
	# Serves /web/index.html
	return app.send_static_file("index.html")

if __name__ == "__main__":
	app.run(host="0.0.0.0", port=1234)