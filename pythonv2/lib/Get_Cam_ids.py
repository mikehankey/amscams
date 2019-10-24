import json
from lib.Cleanup_Json_Conf import cleanup_json, PATH_TO_CONF_JSON

def get_the_cam_ids():
    json_path = cleanup_json()
    toReturn = []
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)
        for cam in data['cameras']:
            toReturn.append(cam['id']) 
    return toReturn

# GET ALL CAMERAS INFO FROM THE OLD VERSION
def get_the_cameras():
    json_path = PATH_TO_CONF_JSON
    toReturn = []
    with open(json_path, "r+") as jsonFile:
         data = json.load(jsonFile)
         for cam in data['cameras']:
            print("IN get_the_cameras")
            print(cam)
            toReturn.append(cam) 
    return toReturn