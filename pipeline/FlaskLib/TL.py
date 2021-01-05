from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template

import psutil
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir
import requests, json
import sys
import netifaces
import os
import subprocess



def tl_menu(amsid):
   jc = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "live.html", jc)
   out = make_default_template(amsid, "tl_menu.html", jc)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)


