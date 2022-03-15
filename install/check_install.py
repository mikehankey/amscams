#!/usr/bin/python3
import os
import json

def load_json_file(json_file):
   try:
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   except:
      json_data = None
   return json_data

def save_json_file(json_file, json_data, compress=False):
   try:
      with open(json_file, 'w') as outfile:
         if(compress==False):
            json.dump(json_data, outfile, indent=4, allow_nan=True )
         else:
            json.dump(json_data, outfile, allow_nan=True)
      outfile.close()
   except:
      print("Failed to save ", json_file)

json_conf = load_json_file("/home/ams/amscams/conf/as6.json")
station_id = json_conf['site']['ams_id']
vpn_file = "/etc/openvpn/" + station_id + ".ovpn"
os.system("df -h > df.txt")
fp = open("df.txt")
data_drive = ""
root_drive = ""
cloud_drive = ""
for line in fp:
   el = line.split()
   mnt = el[-1]
   if "/mnt/ams2" in mnt:
      data_drive = el[-2] 
   if mnt == "/" :
      root_drive = el[-2] 
   if "archive.allsky.tv" in mnt:
      cloud_drive = el[-2] 

print("""
Root Drive  : {:s}
Data Drive  : {:s}
Cloud Drive : {:s}
""".format(data_drive, root_drive, cloud_drive))

# Check if cloud drive is attached.
# if not check if wasabi file exists
# if not try to get key, install & mount and check again
# save results and last attempt time
if cloud_drive == "":
   print("Cloud Drive is not attached.")
   check_install_wasabi_key()
if os.path.exists(vpn_file) is False:
   check_install_vpn()
