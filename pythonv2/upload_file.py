#!/usr/bin/python3

from urllib import request,  parse

import requests
import os
import mimetypes
import sys

meteor_day = sys.argv[1]
station_name = sys.argv[2]
device_name = sys.argv[3]
event_id = sys.argv[4]
file_type = sys.argv[5]
local_filename = sys.argv[6]

# The File to send
file = local_filename
_file = {'files': open(file, 'rb')}

#print(_file)

# The Data to send with the file
api_key = "test"
_data= {'api_key': api_key, 'meteor_day': meteor_day, 'station_name': station_name, 'device_name': device_name, 'format' : 'json', 'event_id' : event_id, 'file_type': file_type}
url = 'http://54.214.104.131/pycgi/api-upload.py'

session = requests.Session()
del session.headers['User-Agent']
del session.headers['Accept-Encoding']

with requests.Session() as session:
    response = session.post(url, data= _data, files=_file)

#print(_data)
#print(_file)

print (response.text)
response.raw.close()


url = 'http://54.214.104.131/pycgi/api-upload.py'
