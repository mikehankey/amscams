import glob, os, os.path, sys 
import cgitb
import json
from pathlib import Path 
from os.path import isfile, join, exists

PATH_TO_CONF_JSON = "/home/ams/amscams/conf/as6.json"
#PATH_TO_CONF_JSON = "/home/ams/amscams/conf/testconf.json"
PATH_TO_CLEAN_CONF_JSON = "/home/ams/amscams/conf/testconf-clean.json"

# Test if the clean versio already exist
file_org = Path(PATH_TO_CONF_JSON)
file_to_clean = Path(PATH_TO_CLEAN_CONF_JSON)

if file_to_clean.is_file():
    #ADD POSSIBILITY TO Erase?
    print("Clean version already exists") 
    exit()
elif file_org.is_file() == False: 
    print("Conf file is missing") 
    exit()
else: 
    #Open the Json Conf & Load the data
    with open(PATH_TO_CONF_JSON, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            print("Impossible to read or parse the conf file ("+PATH_TO_CONF_JSON+")") 
            exit()
    #Create new (clean) array to create clean conf file
    clean_data = {}
    clean_data["cameras"] = []

    #Loop through the cams
    for cam_nb in data["cameras"]: 
        cur_cam = {} 
        cur_cam["id"] = data["cameras"][cam_nb]["cams_id"]
        cur_cam["v"] = int(data["cameras"][cam_nb]["cam_version"])
        cur_cam["ip"] = data["cameras"][cam_nb]["ip"]
        cur_cam["ref"] = str(cam_nb)
        cur_cam["sd"] = {}
        cur_cam["sd"]['url'] = data["cameras"][cam_nb]["sd_url"]
        #Sort SD Masks 
        mask_keys_sorted = sorted(data["cameras"][cam_nb]["masks"])
        cur_cam["sd"]['masks'] = []
        for mask in mask_keys_sorted:
            cur_cam["sd"]['masks'].append(data["cameras"][cam_nb]["masks"][mask])
        cur_cam["hd"]  = {}
        cur_cam["hd"]['url'] = data["cameras"][cam_nb]["hd_url"]        
        #Sort HD Masks 
        mask_keys_sorted = sorted(data["cameras"][cam_nb]["hd_masks"])
        cur_cam["hd"]['masks'] = []
        for mask in mask_keys_sorted:
            cur_cam["hd"]['masks'].append(data["cameras"][cam_nb]["hd_masks"][mask])
        clean_data["cameras"].append(cur_cam)

    print(str(clean_data))

    #Then we take care of the cam settings
    clean_data["cam_settings"] = []
    for setting in data["camera_settingsv1"]:
        night



    print(str(clean_data))
    exit()

        #clean_data["cameras"].append({   \
        #    "id"    : data["cameras"][cam_nb]["cams_id"], \ 
        #    "v"     : data["cameras"][cam_nb]["cam_version"], \
        #    "sd"    :   {   "url": data["cameras"][cam_nb]["sd_url"], \
        #                    "masks": data["cameras"][cam_nb]["masks"]  \
        #                }   
        #    })
        

        #for key in sorted(mydict):
        #print "%s: %s" % (key, mydict[key])
        