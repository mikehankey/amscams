#!/usr/bin/python3

from lib.FileIO import load_json_file

json_conf = load_json_file("/home/ams/amscams/conf/as6.json")

from lib.WebUI import controller
print("Content-type: text/html\n\n")
controller(json_conf)
