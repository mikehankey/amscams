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


def config_vars(amsid, data=None):

  
   jc = load_json_file("../conf/as6.json")

   fields =['operator_name', 'obs_name', 'operator_email', 'operator_state', 'operator_city', 'operator_country', 'operator_device', 'device_lat', 'device_lng', 'device_alt']
   if data is not None:
      print("UPDATE DATA", data)
      for field in fields:
         if field in data:
            print("FIELD:", data[field])
            if data[field] is not None:
               jc['site'][field] = data[field]
         else:
            print("MISSING FIELD:", field )
            jc['site'][field] = ""
      save_json_file("../conf/as6.json", jc)

   print(str(jc['site']))


   template = make_default_template(amsid, "live.html", jc)
   out = make_default_template(amsid, "config_form.html", jc)
   si = jc['site']
   for field in fields:
      if field not in si:
         si[field] = ""
   cam_rows = ""



   cam_rows += "<tr><td>Camera ID</td><td>RTSP URL</td></tr>"
   for cam in jc['cameras']:
      cam_id = jc['cameras'][cam]['cams_id']
      camd = cam.replace("cam", "")
      cam_rows += "<tr ><td >Camera " + camd + " - " + cam_id + "</td><td>rtsp://" + jc['cameras'][cam]['ip'] + jc['cameras'][cam]['sd_url'] + "</td></tr>"
      late_url = "/mnt/ams2/latest/" + cam_id + ".jpg"
      vlate_url = late_url.replace("/mnt/ams2", "")
      #out += "<img width=640 height=360 src=" + vlate_url + ">"

   
   try:
      mac_info = get_mac_info()
   except:
      mac_info = {}


   drive_html = get_disk_info(jc)

   try:
      disk_info = get_disk_info()
   except:
      print("DISK INFO FAILED!")
      disk_info = {}

   net_html = ""
   for i in mac_info:
      net_html += "<tr><td>" + i + "</td><td>" + mac_info[i]['mac_addr'] + "</td>"
      if "ip" in mac_info[i]:
         net_html += "<td>" + mac_info[i]['ip'] + "</td></tr>"
      else:
         net_html += "<td>link down</td></tr>"

 
   #for field in fields:
   #   if field not in si:
   #      si[field] = ""

   out = out.replace("{OBSV_NAME}", si['obs_name'])
   out = out.replace("{NETWORK_INFO}", net_html)
   out = out.replace("{DISK_INFO}", drive_html)
   out = out.replace("{OPERATOR_NAME}", si['operator_name'])
   out = out.replace("{OPERATOR_EMAIL}", si['operator_email'])
   out = out.replace("{OPERATOR_STATE}", si['operator_state'])
   out = out.replace("{OPERATOR_CITY}", si['operator_city'])
   out = out.replace("{OPERATOR_COUNTRY}", si['operator_country'])
   out = out.replace("{DEVICE_LAT}", si['device_lat'])
   out = out.replace("{DEVICE_LON}", si['device_lng'])
   out = out.replace("{DEVICE_ALT}", si['device_alt'])
   out = out.replace("{CAMERA_INFO}", cam_rows)
   template = template.replace("{MAIN_TABLE}", out)
   return(template)


def get_mac_info():
   mac_info = {}
   cmd = "ip a"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   lines = output.split("\n")
   for line in lines:
      if "loop" in line or "inet6" in line or "127.0" in line: 
         continue
      elif "inet" in line: 
         el = line.split(" ")
         ip = el[5].split("/")[0]
         ip = ip.replace(" ", "")
         mac_info[inter]['ip'] = ip
      elif "BROADCAST" in line: 
         el = line.split(":")
         inter = el[1]
         inter = inter.replace(" ", "")
         if inter not in mac_info:
            mac_info[inter] = {}
      elif "link/ether" in line: 
         el = line.split(" ")
         mac = el[5].replace(" ", "")
         mac_info[inter]['mac_addr'] = mac 

   return(mac_info)

def get_disk_info(jc):
   hdd = psutil.disk_usage('/')
   root_tot = int(hdd.total) / (2**30)
   root_used = int(hdd.used) / (2**30)
   root_free = int(hdd.free) / (2**30)

   if "data_dir" in jc:
      data_dir = jc['data_dir']
   else:
      data_dir = "/mnt/ams2"
   hdd = psutil.disk_usage(data_dir)
   data_tot = int(hdd.total) / (2**30)
   data_used = int(hdd.used) / (2**30)
   data_free = int(hdd.free) / (2**30)

   drive_info = """
   <tr><td colspan=2>Root Drive /</td></tr>
   <tr><td>Total: </td><td>{:0.0f} GB</td></tr>
   <tr><td>Used: </td><td>{:0.0f} GB</td></tr>
   <tr><td>Free: </td><td>{:0.0f} GB</td></tr>
   """.format(root_tot, root_used, root_free)

   if data_tot == root_tot:
      drive_info +=  "<tr><td colspan=2>Data Drive Not Connected</td></tr>"
   else:
      drive_info += """
         <tr><td colspan=2>Data Drive {:s}</td></tr>
         <tr><td>Total: </td><td>{:0.0f} GB</td></tr>
         <tr><td>Used: </td><td>{:0.0f} GB</td></tr>
         <tr><td>Free: </td><td>{:0.0f} GB</td></tr>
      """.format(  data_dir, data_tot, data_used, data_free)

   if "cloud_dir" in jc:
      print("CLOUD DIR:", jc['cloud_dir'])
      cloud_dir = jc['cloud_dir']
      cdd = psutil.disk_usage(cloud_dir)
      cl_tot = int(cdd.total) / (2**30)
      cl_used = int(cdd.used) / (2**30)
      cl_free = int(cdd.free) / (2**30)
      if cl_tot == root_tot:
         drive_info +=  "<tr><td colspan=2>Cloud Drive Not Connected</td></tr>"
      else:
         drive_info += """
         <tr><td colspan=2>Cloud Drive {:s}</td></tr>
         <tr><td>Total: </td><td>{:0.0f} GB</td></tr>
         <tr><td>Used: </td><td>{:0.0f} GB</td></tr>
         <tr><td>Free: </td><td>{:0.0f} GB</td></tr>
         """.format(cloud_dir, cl_tot, cl_used, cl_free)


   return (drive_info)
