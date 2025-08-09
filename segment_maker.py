import json
import datetime


line_1 = "0021|0023|0026,0027|0608,0039|0042,0045|0046,0049|0052,0053|0066,0067|0074,0081|0191|0192,0195,K195|0196,0201,W201|0202,0205|0206|0212,0209|0216,0221"
line_2 = "0022|0024|0028,0607|0034|0044,0047|0048,0051|0054,0055|0068,0069|0076,0083|0193|0194,0197|0198,0203|0204,0207,K204|0208,W208|0214,0211|0218,0223"
line_3 = "6059|6061|6064,6063|6055|6072,6073|6076,6075|6082,6079|6086|6096,0057|0070,0071|3951|3953|3955|3957|3959|3975|3977"
line_4 = "6058|6060|6066,6069|6074|6080|6084|6090,6083|6092|6098,0059|0072,0093|0078|3952|3954|3958|3962,3973|3970|3974|3976"



segmentMap = {}
segmentCount = 0


messageTypes = ['CA_MSG','CB_MSG','CC_MSG']


def addSeg(line,name):
    global segmentMap, segmentCount
    segments = line.split('|')
   
    for seg in segments:   
        segmentCountString = 'SEGMENT{0:02}'.format(segmentCount)
        segmentMap[segmentCountString] = {}
        segmentMap[segmentCountString]['name'] = name
        segmentMap[segmentCountString]['signals'] = []
        signals = seg.split(',')
        for signal in signals:
            segmentMap[segmentCountString]['signals'].append(signal)
        segmentMap[segmentCountString]['trains'] = []
        segmentCount += 1

def make_segments():
    addSeg(line_1,'Line_1')
    addSeg(line_2,'Line_2')
    addSeg(line_3,'Line_3')
    addSeg(line_4,'Line_4')
    # print('SEGMENT MAP: ',segmentMap)
    return segmentMap

def main_fut():
    Loco = {}
    with open('td_test_data__2025_07_29.json','r') as file:
        for line in file:
            # print(line.strip())
            data = json.loads(line)
            for item in data:
                action = data[item]
                if('descr' in action):
                    train = action['descr']
                    if not train in Loco:
                        Loco[train] = []
                    trainTime = 0
                    trainFrom = '-'
                    trainTo = '-'
                    localTime = 0
                    if 'time' in action:
                        trainTime = action['time']
                        unix_timestamp_sec = int(trainTime)/1000
                        dt = datetime.datetime.fromtimestamp(unix_timestamp_sec)
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                    if 'to' in action:
                        trainTo = action['to']
                    if 'from' in action:
                        trainFrom = action['from']
                    movement = {'time': trainTime, 'localtime': formatted_date,  'from': trainFrom, 'to': trainTo}
                    Loco[train].append(movement)
                else:
                    print(data)
    print('vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv')
    with open('movements.txt','w') as of:
        for train,movements in Loco.items():
            print(train)
            of.write(train + '\r\n')
            for movement in movements:
                print(movement)
                of.write(str(movement) + '\r\n')
    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^')


# main()