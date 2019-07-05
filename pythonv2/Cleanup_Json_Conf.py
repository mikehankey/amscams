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
    for cam_nb in sorted(data["cameras"]): 
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
    #print(str(clean_data))
    #Then we take care of the cam settings
    clean_data["cam_settings"] = []
    for setting in data["camera_settingsv1"]:
        cur_settings = {}
        cur_settings["brightness"] = int(data["camera_settingsv1"][setting]["brightness"])
        cur_settings["gamma"] = int(data["camera_settingsv1"][setting]["gamma"])
        cur_settings["BLC"] = int(data["camera_settingsv1"][setting]["BLC"])
        cur_settings["contrast"] = int(data["camera_settingsv1"][setting]["contrast"])
        clean_data["cam_settings"].append(cur_settings)
    #Then the site
    clean_data["site"]= [] 
    cur_site = {}
    cur_site['device_alt'] = float(data["site"]["device_alt"])
    cur_site['device_lng'] =  float(data["site"]["device_lng"]) 
    cur_site['device_lat'] =  float(data["site"]["device_lat"]) 
    cur_site['api_key'] =  data["site"]["api_key"] 
    cur_site['cams_pwd'] =  data["site"]["cams_pwd"] 
    cur_site['cams_dir'] =  data["site"]["cams_dir"] 
    cur_site['operator_name'] =  data["site"]["operator_name"] 
    cur_site['proc_dir'] =  data["site"]["proc_dir"] 
    cur_site['mac_addr'] =  data["site"]["mac_addr"] 
    cur_site['city'] =  data["site"]["operator_city"] 
    cur_site['ams_id'] =  data["site"]["ams_id"] 
    cur_site['pwd'] =  data["site"]["pwd"] 
    cur_site['sd_video_dir'] =  data["site"]["sd_video_dir"] 
    cur_site['hd_video_dir'] =  data["site"]["hd_video_dir"] 
    cur_site['cal_dir'] =  data["site"]["cal_dir"] 
    cur_site['obs_name'] =  data["site"]["obs_name"] 
    cur_site['operator_email'] =  data["site"]["operator_email"] 
    cur_site['cams_queue_dir'] =  data["site"]["cams_queue_dir"] 
    cur_site['operator_state'] =  data["site"]["operator_state"] 
    if(data["site"]["operator_country"] is None):
        cur_site['operator_country'] =  'US'
    else:
        cur_site['operator_country'] =  data["site"]["operator_country"]   
    clean_data["site"].append(cur_site)         
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
        