import json
import sys
from lib.Cleanup_Json_Conf import cleanup_json, PATH_TO_CONF_JSON

def get_the_cam_position():
    json_path = cleanup_json()
    toReturn = []
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)
        print("<hr>JSON CONF<hr>")
        print(data)
        sys.exit(0)
        for cam in data['cameras']:
            toReturn.append(cam['id']) 
    return toReturn
 