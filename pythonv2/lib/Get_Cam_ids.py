import json
from lib.Cleanup_Json_Conf import cleanup_json

def get_the_cam_ids():
    json_path = cleanup_json()
    toReturn = []
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)
        for cam in data['cameras']:
            toReturn.append(cam['id']) 
    return toReturn