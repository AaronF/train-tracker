from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('index.html')

@app.route('/trains')
def trains():
	try:
		with open('nearby_trains.json', 'r') as file:
			data = json.load(file)
	except:
		data = []
	return jsonify(data)

# if __name__ == '__main__':
# 	app.run(debug=True)