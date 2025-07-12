import os, stomp, json, time
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from collections import OrderedDict

load_dotenv()

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.username_pw_set(os.getenv('MQTT_USERNAME'),os.getenv('MQTT_PASSWORD'))
mqttc.connect(os.getenv('MQTT_HOST'), 1883, 60)
mqttc.loop_start()

AREA = 'KG'

SIGNALS_TO_WATCH = {
	'0078' : {
		'dir' : 'South'
	},
	'3952' : {
		'dir' : 'South'
	},
	'3953' : {
		'dir' : 'North'
	},
	'3954' : {
		'dir' : 'South'
	},
	'3955' : {
		'dir' : 'North'
	},
	'3957' : {
		'dir' : 'North'
	},
	'3958' : {
		'dir' : 'South'
	},
	'3959' : {
		'dir' : 'North'
	},
	'3973' : {
		'dir' : 'North'
	},
	'3975' : {
		'dir' : 'North'
	},
}

NORTH_OD = OrderedDict()
NORTH_OD = {
	'3953' : [],
	'3955' : [],
	'3957' : [],
	'3959' : []
}

SOUTH_OD = OrderedDict()
SOUTH_OD = {
	'3952' : [],
	'3954' : [],
	'3958' : []
}

class Listener(stomp.ConnectionListener):
	def on_message(self, frame):
		data = json.loads(frame.body)
		for item in data:
			for key, value in item.items():
				if key in ['CA_MSG', 'CB_MSG', 'CC_MSG', 'CT_MSG']:
					if value.get('area_id') == AREA:
						# print(f"Key: {key}")
						# print(f"Value: {value}")

						if ('from' in value and value['from'] in SIGNALS_TO_WATCH) or ('to' in value and value['to'] in SIGNALS_TO_WATCH):
							# print(f"Key: {key}")

							signal_info = {
								'time' : value['time'] if 'time' in value else None,
								'from' : value['from'] if 'from' in value else None,
								'to' : value['to'] if 'to' in value else None,
								'head_code' : value['descr'] if 'descr' in value else None,
							}

							if value['to'] in SIGNALS_TO_WATCH:
								signal_info['direction'] = SIGNALS_TO_WATCH[value['to']]['dir']
								# print(f"Value: {value}")
								# print('Direction', SIGNALS_TO_WATCH[value['to']]['dir'])
							elif value['from'] in SIGNALS_TO_WATCH:
								signal_info['direction'] = SIGNALS_TO_WATCH[value['from']]['dir']
								# print(f"Value: {value}")
								# print('Direction', SIGNALS_TO_WATCH[value['from']]['dir'])

							# [1, 1, 0, 0, 0, 0]

							print(signal_info)

							for key, value in NORTH_OD.items():
								if signal_info['head_code'] in value:
									value.remove(signal_info['head_code'])
							for key, value in SOUTH_OD.items():
								if signal_info['head_code'] in value:
									value.remove(signal_info['head_code'])
							
							if signal_info['from'] != None and signal_info['from'] in NORTH_OD:
								NORTH_OD[signal_info['from']].append(signal_info['head_code'])
							if signal_info['to'] != None and signal_info['to'] in NORTH_OD:
								NORTH_OD[signal_info['to']].append(signal_info['head_code'])
							if signal_info['from'] != None and signal_info['from'] in SOUTH_OD:
								SOUTH_OD[signal_info['from']].append(signal_info['head_code'])
							if signal_info['to'] != None and signal_info['to'] in SOUTH_OD:
								SOUTH_OD[signal_info['to']].append(signal_info['head_code'])

							print('North', NORTH_OD)
							print('South', SOUTH_OD)

							# mqttc.publish('trains/signals', json.dumps(signal_info))

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)], heartbeats=(15000, 15000))
conn.set_listener('', Listener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination=f'/topic/TD_ALL_SIG_AREA', id=1, ack='auto')

while True:
	time.sleep(5)

	mqttc.publish('trains/signals/north', json.dumps(NORTH_OD))
	mqttc.publish('trains/signals/south', json.dumps(SOUTH_OD))
