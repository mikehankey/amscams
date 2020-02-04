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


# Return all HD masks
def get_masks():
    json_path = cleanup_json()
    toReturn = []
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)
        for cam in data['cameras']:
           if("hd" in cam):
              if("masks" in cam['hd']):
               toReturn.append(cam['hd']['masks']) 
    return toReturn

# Return all HD masks for a given camera
def get_mask(cam_id):
    print("IN GET MASK<br>" + cam_id)
    json_path = cleanup_json()
    toReturn = [] 
    with open(json_path, "r+") as jsonFile:
        data = json.load(jsonFile)
     
        for cam in data['cameras']:
           if("id" in cam):
              print("<br/>CAM ID " + cam['id'])
              print("<br/>cam ")
              print(cam_id) 
              if(cam['id']==cam_id): 
                  print("<br>TEST OK<br>")
                  toReturn = cam['hd']['masks']

    print("TO RETURN <br>")
    print(toReturn)
    return toReturn   


# GET ALL CAMERAS INFO FROM THE OLD VERSION
def get_the_cameras():
    json_path = PATH_TO_CONF_JSON
    toReturn = []
    with open(json_path, "r+") as jsonFile:
         data = json.load(jsonFile)
         return data['cameras']