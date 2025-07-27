import json
import datetime



messageTypes = ['CA_MSG','CB_MSG','CC_MSG']

def main():
    Loco = {}
    with open('td_test_data__2025_07_25.json','r') as file:
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
                    trainFrom = 0
                    trainTo = 0
                    localTime = 0
                    if 'time' in action:
                        trainTime = action['time']
                        unix_timestamp_ms = int(trainTime)
                        unix_timestamp_sec = unix_timestamp_ms / 1000
                        dt_object_local = datetime.datetime.fromtimestamp(unix_timestamp_sec)
                        formatted_date = dt_object_local.strftime("%Y-%m-%d %H:%M:%S")
                    if 'to' in action:
                        trainTo = action['to']
                    if 'from' in action:
                        trainFrom = action['from']
                    movement = {'time': trainTime, 'localtime': formatted_date,  'from': trainFrom, 'to': trainTo}
                    Loco[train].append(movement)
                else:
                    print(data)

    for train,movements in Loco.items():
        print(train)
        for movement in movements:
            print(movement)


main()