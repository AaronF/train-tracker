import os
import stomp
import json
import time

from dotenv import load_dotenv

load_dotenv()

# TIPLOCS_OF_INTEREST = ['KETTRNGJ', 'MARKTHRB']
STANOX_OF_INTEREST = ['59421', '61006', '59401'] # Des, Ket, Mark
NEARBY_TRAINS_FILE = 'nearby_trains.json'

class TrainListener(stomp.ConnectionListener):
	def on_error(self, frame):
		print('received an error "%s"' % frame)
	def on_message(self, frame):
		# print('received a message "%s"' % frame)
		data = json.loads(frame.body)
		# print('Received data:', data)

		filtered = []

		for item in data:
			if 'body' in item:
				body = item.get('body', {})
				if 'loc_stanox' in body and body['loc_stanox'] in STANOX_OF_INTEREST:
					time_string = int(body['actual_timestamp']) / 1000 if 'actual_timestamp' in body else 0
					train_info = {
						'train_id': body['train_id'] if 'train_id' in body else 'N/A',
						'loc_stanox': body['loc_stanox'] if 'loc_stanox' in body else 'N/A',
						'time': time.strftime('%H:%M:%S', time.localtime(time_string)),
					}
					filtered.append(train_info)

		# print('Filtered trains:', filtered)
		# try:
		# 	with open(NEARBY_TRAINS_FILE, 'r') as file:
		# 		trains = json.load(file)
		# except:
		# 	trains = []
		# trains.append(filtered)
		# trains = trains[-10:]  # Keep only the last 10 trains
		with open(NEARBY_TRAINS_FILE, 'a') as file:
			json.dump(filtered, file)

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)])
conn.set_listener('', TrainListener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination='/topic/TRAIN_MVT_ALL_TOC', id=1, ack='auto')

while True:
	time.sleep(5)