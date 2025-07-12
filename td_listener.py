import os, stomp, json, time
from dotenv import load_dotenv

load_dotenv()

OBSERVED = set()
AREA = 'KG'

SIGNALS_TO_WATCH = {
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
}

class Listener(stomp.ConnectionListener):
	def on_message(self, frame):
		data = json.loads(frame.body)
		for item in data:
			for key, value in item.items():
				if key in ['CA_MSG', 'CB_MSG', 'CC_MSG', 'CT_MSG']:
					# print(f"Key: {key}")
					# print(f"Value: {value.get('area_id')}")

					if value.get('area_id') == AREA:
						# print(f"Key: {key}")
						# print(f"Value: {value}")

						if ('from' in value and value['from'] in SIGNALS_TO_WATCH) or ('to' in value and value['to'] in SIGNALS_TO_WATCH):
							# print(f"Key: {key}")
							print(f"Value: {value}")
							if value['to'] in SIGNALS_TO_WATCH:
								print('Direction', SIGNALS_TO_WATCH[value['to']]['dir'])

		# if data.get('area_id') == AREA:
		# 	OBSERVED.add(data.get('berth_id'))
		# 	if len(OBSERVED) % 20 == 0:
		# 		print("Seen so far:", sorted(list(OBSERVED))[:50])

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)], heartbeats=(15000, 15000))
conn.set_listener('', Listener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination=f'/topic/TD_ALL_SIG_AREA', id=1, ack='auto')

while True:
	time.sleep(5)
