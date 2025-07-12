import os
import stomp
import json
import time
import paho.mqtt.client as mqtt

from dotenv import load_dotenv

load_dotenv()

# TIPLOCS_OF_INTEREST = ['KETTRNGJ', 'MARKTHRB']
# STANOX_OF_INTEREST = ['59421', '61006', '59401', '61100', '61009'] # Des, Ket N jn, Mark, Wel, Ket
STANOX_LOOKUP = {
	'61010' : {
		'name' : 'Kettering South Jn',
		'is_active' : False,
		'is_term' : False,
		'term_dir' : ''
	},
	'61009' : {
		'name' : 'Kettering',
		'is_active' : True,
		'is_term' : True,
		'term_dir' : 'UP'
	},
	'61006' : {
		'name' : 'Kettering North Jn',
		'is_active' : True,
		'is_term' : False,
		'term_dir' : ''
	},
	'59421' : {
		'name' : 'Desborough Jn',
		'is_active' : True,
		'is_term' : False,
		'term_dir' : ''
	},
	'59411' : {
		'name' : 'Braybrook',
		'is_active' : True,
		'is_term' : False,
		'term_dir' : ''
	},
	'60011' : {
		'name' : 'Corby',
		'is_active' : True,
		'is_term' : True,
		'term_dir' : 'DOWN'
	},
	'59139' : {
		'name' : 'Manton Jn',
		'is_active' : False,
		'is_term' : False,
		'term_dir' : ''
	},
	'59401' : {
		'name' : 'Market Harborough',
		'is_active' : True,
		'is_term' : True,
		'term_dir' : 'DOWN'
	}
}
NEARBY_TRAINS_FILE = 'nearby_trains.json'
nearby_trains = {}

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# mqttc.on_connect = on_mqtt_connect
# mqttc.on_message = on_message
mqttc.username_pw_set(os.getenv('MQTT_USERNAME'),os.getenv('MQTT_PASSWORD'))
mqttc.connect(os.getenv('MQTT_HOST'), 1883, 60)
mqttc.loop_start()

class TrainListener(stomp.ConnectionListener):
	global nearby_trains
	filtered = []

	def on_error(self, frame):
		print('received an error "%s"' % frame)
	def on_message(self, frame):
		data = json.loads(frame.body)

		for item in data:
			if 'body' in item:
				body = item.get('body', {})
				if 'loc_stanox' in body and body['loc_stanox'] in STANOX_LOOKUP and STANOX_LOOKUP[body['loc_stanox']]['is_active'] == True and 'event_type' in body and 'direction_ind' in body:
					time_string = int(body['actual_timestamp']) / 1000 if 'actual_timestamp' in body else 0
					train_info = {
						'train_id': body['train_id'] if 'train_id' in body else 'N/A',
						'train_service_code': body['train_service_code'] if 'train_service_code' in body else 'N/A',
						'loc_stanox': body['loc_stanox'] if 'loc_stanox' in body else 'N/A',
						'loc_name': STANOX_LOOKUP.get(body.get('loc_stanox'), {}).get('name', 'N/A'),
						'next_report_stanox': body['next_report_stanox'] if 'next_report_stanox' in body else 'N/A',
						'next_loc_name': STANOX_LOOKUP.get(body.get('next_report_stanox'), {}).get('name', 'N/A'),
						'event_type': body['event_type'] if 'direction_ind' in body else 'N/A',
						'direction_ind': body['direction_ind'] if 'direction_ind' in body else 'N/A',
						'train_terminated': body['train_terminated'] if 'train_terminated' in body else 'N/A',
						'time': time.strftime('%H:%M:%S', time.localtime(time_string)),
					}
					self.filtered.append(train_info)

					print('Train', train_info['train_id'], 'has', train_info['event_type'], train_info['loc_name'], ', the next destination is', train_info['next_loc_name'])

					if STANOX_LOOKUP[train_info['loc_stanox']]['is_term'] == True and STANOX_LOOKUP[train_info['loc_stanox']]['term_dir'] == train_info['direction_ind'] and train_info['event_type'] == "DEPARTURE":
						if train_info['train_id'] in nearby_trains:
							nearby_trains.pop(train_info['train_id'])
					else:
						nearby_trains[train_info['train_id']] = train_info

					print(nearby_trains)

		# with open(NEARBY_TRAINS_FILE, 'w') as file:
		# 	json.dump(self.filtered, file)

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)], heartbeats=(15000, 15000))
conn.set_listener('', TrainListener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination='/topic/TRAIN_MVT_ALL_TOC', id=1, ack='auto')

while True:
	time.sleep(5)

	# Convert dictionary of trains to valid array for JSON parsing
	trains_array = []
	for key, value in nearby_trains.items():
		trains_array.append(value)

	mqttc.publish('trains/passing', json.dumps(trains_array))