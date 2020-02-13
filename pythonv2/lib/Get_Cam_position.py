import json
import sys
from lib.Cleanup_Json_Conf import cleanup_json, PATH_TO_CONF_JSON

def get_the_cam_position():
    json_path = cleanup_json()
    toReturn = {}
    with open(json_path, "r+") as jsonFile:
         data = json.load(jsonFile)
         if('geoloc' in data):
            if('lat' in data['geoloc']):
               toReturn['lat'] = data['geoloc']['lat']
            if('lng' in data['geoloc']):
               toReturn['lng'] = data['geoloc']['lng']
            if('alt' in data['geoloc']):
               toReturn['alt'] = data['geoloc']['alt']
    return toReturn
 

def get_device_position():
    json_path = cleanup_json()
    toReturn = {}
    with open(json_path, "r+") as jsonFile:
         data = json.load(jsonFile)
         if('geoloc' in data):
            if('lng' in data['geoloc']):
               toReturn['lng'] = data['geoloc']['lng']
            if('lat' in data['geoloc']):
               toReturn['lat'] = data['geoloc']['lat']
            if('alt' in data['geoloc']):
               toReturn['alt'] = data['geoloc']['alt']
    return toReturn


