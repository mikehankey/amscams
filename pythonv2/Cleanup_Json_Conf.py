import glob, os, os.path, sys 
import cgitb
import json
from pathlib import Path 
from os.path import isfile, join, exists


#PATH_TO_CONF_JSON = "/home/ams/amscams/conf/as6.json"

PATH_TO_CONF_JSON = "/home/ams/amscams/conf/testconf.json"
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

    #First we loop through the cams
    for cam in data["cameras"]:
        print(str(cam)) #The order of the cam
        print(cam['cams_id']) #The order of the cam
