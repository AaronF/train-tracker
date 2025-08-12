import os, stomp, json, datetime, time, segment_maker, logging
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.username_pw_set(os.getenv('MQTT_USERNAME'),os.getenv('MQTT_PASSWORD'))
mqttc.connect(os.getenv('MQTT_HOST'), 1883, 60)
mqttc.loop_start()

SEGMENTS = segment_maker.make_segments()
AREA = ['KG','WG']

logging.basicConfig(
	level=logging.INFO,
	format='[%(asctime)s] %(levelname)s: %(message)s',
)

# def to_segment(action):
# 	if 'descr' in action and 'to' in action:
# 		train = action['descr']
# 		signal = action['to']

# 		current_segment = None
# 		target_segment = None

# 		for segment_name, segment in SEGMENTS.items():
# 			if train in segment['trains']:
# 				current_segment = (segment_name, segment)
# 			if signal in segment['signals']:
# 				target_segment = (segment_name, segment)

# 		if current_segment:
# 			current_segment[1]['trains'].remove(train)

# 		if target_segment:
# 			target_segment[1]['trains'].clear()
# 			target_segment[1]['trains'].append(train)

# 		# if current_segment or target_segment:
# 			# print("---")
# 			# current_segment and print("remove " + train + " from " + current_segment[0])
# 			# target_segment and print("add " + train + " to " + target_segment[0])
# 	if 'descr' in action and 'from' in action and not 'to' in action:
# 		train = action['descr']

# 		for segment_name, segment in SEGMENTS.items():
# 			if train in segment['trains']:
# 				segment['trains'].remove(train)

def to_segment(action):
	train = action.get('descr')
	if not train:
		return

	# Train moving to a new signal
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

	# Train leaving without a target
	if 'from' in action:
		for segment in SEGMENTS.values():
			if train in segment['trains']:
				segment['trains'].remove(train)
				break


def load_from_test_file():
	with open('td_test_data__2025_08_01.json','r') as file:
		for line in file:
			data = json.loads(line)
			for item in data:
				action = data[item]

				to_segment(action)
				# time.sleep(0.5)

def print_segments():
	global SEGMENTS
	current_line = ""
	for signal in SEGMENTS:
		if current_line != SEGMENTS[signal]['name']:
			print("\n", SEGMENTS[signal]['name'])
			current_line = SEGMENTS[signal]['name']
		if not SEGMENTS[signal]['trains']:
			print("__", end = "")
		else:
			print(SEGMENTS[signal]['trains'], end = "")

	print("\n")

class Listener(stomp.ConnectionListener):
	def on_message(self, frame):
		data = json.loads(frame.body)
		for item in data:
			for key, value in item.items():
				if key in ['CA_MSG', 'CB_MSG', 'CC_MSG', 'CT_MSG']:
					if value.get('area_id') in AREA:
						for inner in item:
							action = item[inner]
							to_segment(action)

	def on_error(self, frame):
		logging.error('STOMP error: %s', getattr(frame, 'body', frame))

	def on_disconnected(self):
		logging.warning('Disconnected from STOMP broker')

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)], heartbeats=(15000, 15000))
conn.set_listener('', Listener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination=f'/topic/TD_ALL_SIG_AREA', id=1, ack='auto')

while True:
	if not conn.is_connected():
		logging.warning('Detected disconnect')
	time.sleep(5)
	# print(SEGMENTS)
	print("\n//// TRAINS ////")
	print_segments()

	mqttc.publish('trains/segments', json.dumps(SEGMENTS))

# load_from_test_file()