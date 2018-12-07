#!/usr/bin/python3

import json

json_file = open('as6.json')
json_str = json_file.read()
json_data = json.loads(json_str)
cams = json_data['cameras']['cam1']['ip']

print(cams)
