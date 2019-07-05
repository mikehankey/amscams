import glob, os, os.path, sys 
import cgitb
import json
from pathlib import Path 
from os.path import isfile, join, exists


#PATH_TO_CONF_JSON = "/home/ams/amscams/conf/as6.json"

PATH_TO_CONF_JSON = "/home/ams/amscams/conf/testconf.json"
PATH_TO_CLEAN_CONF_JSON = "/home/ams/amscams/conf/testconf-clean.json"


# Test if the clean versio already exist
js_file = Path(PATH_TO_CLEAN_CONF_JSON)

if js_file.is_file():
    #ADD POSSIBILITY TO Erase?
    print("Clean version already exists") 
    exit()

else:

    #Open the Json Conf & Load the data
    with open(PATH_TO_CONF_JSON, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            print("Impossible to open the conf file ("+PATH_TO_CONF_JSON+")") 
            exit()

    #Create new (clean) array to create clean conf file
    clean_data = {}

    #First we loop through the cams
    for cams in data["cameras"]:
        print(cams)
