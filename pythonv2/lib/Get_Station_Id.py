import json
from lib.Cleanup_Json_Conf import cleanup_json

def get_station_id():
    json_path = cleanup_json() 
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)  
        return data['operator']['ams_id'] 