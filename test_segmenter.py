import json
import datetime

SEGMENTS = {
	'SEG01' : {
		'signals' : ['0053'],
		'trains' : []
	},
	'SEG02' : {
		'signals' : ['0066'],
		'trains' : []
	},
	'SEG03' : {
		'signals' : ['0067'],
		'trains' : []
	},
	'SEG04' : {
		'signals' : ['0074'],
		'trains' : []
	},
	'SEG05' : {
		'signals' : ['0081'],
		'trains' : []
	},
	'SEG06' : {
		'signals' : ['0191'],
		'trains' : []
	},
	'SEG07' : {
		'signals' : ['0192', '0195', 'K195'],
		'trains' : []
	},
	'SEG08' : {
		'signals' : ['0196', '0201', 'W201'],
		'trains' : []
	},
	'SEG09' : {
		'signals' : ['0202', '0205'],
		'trains' : []
	},
	'SEG10' : {
		'signals' : ['0206'],
		'trains' : []
	},
	'SEG11' : {
		'signals' : ['0212'],
		'trains' : []
	},
	'SEG12' : {
		'signals' : ['0209'],
		'trains' : []
	},
}

def main():
	with open('td_test_data__2025_07_31.json','r') as file:
		for line in file:
			data = json.loads(line)
			for item in data:
				action = data[item]
				if 'descr' in action and 'to' in action:
					train = action['descr']
					signal = action['to']

					current_segment = None
					target_segment = None

					for segment_name, segment in SEGMENTS.items():
						if train in segment['trains']:
							current_segment = (segment_name, segment)
						if signal in segment['signals']:
							target_segment = (segment_name, segment)

					if current_segment:
						current_segment[1]['trains'].remove(train)

					if target_segment:
						target_segment[1]['trains'].append(train)

					if current_segment or target_segment:
						print("---")
						current_segment and print("remove " + train + " from " + current_segment[0])
						target_segment and print("add " + train + " to " + target_segment[0])

					# print(json.dumps(SEGMENTS, indent=2))

main()