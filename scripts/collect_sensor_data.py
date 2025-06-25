import json

def collect_sensor_data(data):
    with open('/home/atonye/Bureau/Training_Internship/intern/project/data/sensor_data.json', 'a') as f:
        json.dump(data, f)
        f.write('\n')
