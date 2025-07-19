import os, stomp, json, time, datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from collections import OrderedDict

load_dotenv()

AREA = 'KG'

SIGNALS_TO_WATCH = {
	'0021', '0023', '0022', '0024', '0026', '0028', '0027', '0607', '0602', '0603', '0605', '0604', '0033', '0608', '0039', '0042', '0045', '0047', '0049', '0051', '0052', '0054', '0053', '0055', '0066', '0068', '0067', '0069', '0074', '0076', '0081', '0083', '0191', '0193', '0192', '0194', '0195', '0196', '0201', '0202', '0205', '0206', '0212', '0214', '0209', '0211', '0216', '0218', '0221', '0223', '6059', '6060', '6061', '6064', '6066', '6063', '6065', '6069', '6071', '6070', '0034', '6072', '6074', '6073', '0044', '6076', '6080', '6075', '6082', '6084', '0046', '0048', '6079', '6086', '6090', '6083', '6092', '6085', '6094', '6088', '6078', '0057', '0059', '0070', '0072', '0071', '0093', '0078', '3951', '3953', '3952', '3955', '3954', '3957', '3958', '3959', '3962', '3975', '3973', '3977', '3974', '3976', '3970', '3965', '3963', '3961'
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
							print(f"Item: {item}")

							now = datetime.datetime.now()

							with open('td_test_data__' + now.strftime("%Y_%m_%d") + '.json', 'a') as file:
								file.write(json.dumps(item) + '\n')
								# file.write(item + '\n')
								# json.dump(item, file)

conn = stomp.Connection([('publicdatafeeds.networkrail.co.uk', 61618)], heartbeats=(15000, 15000))
conn.set_listener('', Listener())
conn.connect(os.getenv('NETWORK_RAIL_USERNAME'), os.getenv('NETWORK_RAIL_PASSWORD'), wait=True)
conn.subscribe(destination=f'/topic/TD_ALL_SIG_AREA', id=1, ack='auto')

while True:
	time.sleep(5)
