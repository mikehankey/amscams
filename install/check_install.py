#!/usr/bin/python3
import time
import os
import json
import requests
#


def get_page(url):
   response = requests.get(url)
   content = response.content.decode()
   content = content.replace("\\", "")
   #content = json.loads(content)
   return(content)



def check_install_wasabi_key(station_id):
   
   url = "https://archive.allsky.tv/" + station_id + "/cmd/wasabi.txt"
   wasabi = get_page(url)
   local_key_file = "/home/ams/amscams/conf/wasabi.txt"
   if "Error" in wasabi:
      print(url)
      print("No remote wasabi.")
      #return()
   else:

      if os.path.exists(local_key_file) is False :
         fp = open("/home/ams/amscams/conf/wasabi.txt", "w")
         fp.write(wasabi)
         fp.close()
         os.system("chmod 600 /home/ams/amscams/conf/wasabi.txt")
         os.system("chown ams:ams /home/ams/amscams/conf/wasabi.txt")

   os.system("sudo umount /mnt/archive.allsky.tv")
   os.system("cd /home/ams/amscams/pythonv2; runuser -u ams -- ./wasabi.py mnt")
   if os.path.exists("/home/ams/amscams/conf/wasabi.txt"):
      cmd = "rm /mnt/archive.allsky.tv/" + station_id + "/cmd/wasabi.txt"
      print(cmd)
      os.system(cmd)


def check_install_vpn(station_id):
   url = "https://archive.allsky.tv/" + station_id + "/cmd/" + station_id + ".ovpn"
   print(url)
   vpn = get_page(url)
   print(vpn)

   if "Error" in vpn:
      print("No remote vpn.")
      return()

   fp = open("/etc/openvpn/" + station_id + ".ovpn", "w")
   fp.write(vpn)
   fp.close()
   if os.path.exists("/etc/openvpn/" + station_id + ".ovpn"):
      cmd = "rm /mnt/archive.allsky.tv/" + station_id + "/cmd/" + station_id + ".ovpn"
      print(cmd)
      os.system(cmd)

   

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


# wait until we are online.

for i in range(0,30):
   res = os.system("ping -c1 google.com > /dev/null 2>&1")
   print("PING:", res)
   if res == 0:
      break
   time.sleep(1)



#test = get_page("https://archive.allsky.tv/444.html")
#print(test)
#exit()

fp = open("df.txt")
data_drive = ""
root_drive = ""
cloud_drive = ""
for line in fp:

   el = line.split()
   print("DRIVE:", el)
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
   check_install_wasabi_key(station_id)
if os.path.exists(vpn_file) is False:
   check_install_vpn(station_id)
