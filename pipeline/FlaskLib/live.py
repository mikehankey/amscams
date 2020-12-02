from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template

import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir


def live_view(amsid):
  
   json_conf = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "live.html", json_conf)
   out = ""
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      late_url = "/mnt/ams2/latest/" + cam_id + ".jpg"
      vlate_url = late_url.replace("/mnt/ams2", "")
      out += "<img width=640 height=360 src=" + vlate_url + ">"
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

