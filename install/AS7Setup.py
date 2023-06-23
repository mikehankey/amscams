#!/usr/bin/python3
import netifaces as ni
import pkg_resources
import sys
import os
# see what we have
installed = {pkg.key for pkg in pkg_resources.working_set}

import subprocess
import time
import json
from pathlib import Path
try:
   from consolemenu import *
   from consolemenu.items import *
except:
   os.system("python3 -m pip install consolemenu")
   os.system("python3 -m pip install console-menu")
   from consolemenu import *
   from consolemenu.items import *
try:
   from tabulate import tabulate
except:
   os.system("python3 -m pip install tabulate")
try:
   import requests
except:
   os.system("python3 -m pip install requests")
try:
   import netifaces 
except:
   os.system("python3 -m pip install netifaces")
try:
   import getpass 
except:
   os.system("python3 -m pip install getpass")


class AS7Setup():

   def __init__(self):
      username = getpass.getuser()
      self.setup_file = "/home/ams/amscams/conf/setup.json"
      if self.cfe(self.setup_file) == 1:
         self.user_data = self.load_json_file(self.setup_file)
         if "pin_code" in self.user_data:
            self.pin_code = self.user_data['pin_code']
         else:
            self.pin_code = None
         if "station_id" in self.user_data:
            self.station_id = self.user_data['station_id']
         else:
            self.station_id = None

      else:
         self.user_data = {}
      print(username)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      if username != "root":
         print("""THIS SCRIPT MUST BE RUN AS ROOT! use "sudo"
         sudo python3 AS7Setup.py
         """)
         os.system("cd /home/ams/amscams/install && sudo python3 AS7Setup.py")

         exit()
      print("RUNNING AS ROOT")
      if self.cfe(self.setup_file) == 0:
         self.setup_data = {}
      else:
         try:
            #input("Trying" + self.setup_file)
            self.setup_data = self.load_json_file(self.setup_file)
         except:
            print("Failed to load" + self.setup_file)
            exit()

   def start_up(self):
      # check a few things. 
      # 1 - is this a new install or an existing install?
      # 2 - is there any setup info available
      # 3 - if the station_id and pin_code is not present ask for that first. 
      if os.path.isfile("../conf/as6.json") == 1:
         print("Local conf file exists.")
         self.json_conf = self.load_json_file("../conf/as6.json")
         if "api_key" not in self.json_conf:
            self.json_conf['api_key'] = "123"
         if "multi_station_sync" not in self.json_conf['site']:
            self.json_conf['site']['multi_station_sync'] = []

         needs_setup = 0
      else:
         self.json_conf = {}
         self.json_conf['site'] = {}
         self.json_conf['cameras'] = {}
         self.json_conf['setup'] = {}
      if "setup" not in self.json_conf:
         print("MISSING SETUP")
         needs_setup = 1
      elif "pin_code" not in self.json_conf['setup']:
         print("MISSING PIN")
         needs_setup = 1

      if "ams_id" not in self.json_conf['site'] or needs_setup == 1:
         print("MISSING AMS ID")
         #print("JS:", self.json_conf)
         self.station_id = input("Enter the station ID (AMS??):")
         self.pin_code = input("Enter the station PIN code:")
         self.user_data['pin_code'] = self.pin_code
         self.user_data['station_id'] = self.station_id
         self.json_conf['setup'] = {}
         self.json_conf['setup']['pin_code'] = self.user_data['pin_code']
         self.json_conf['setup']['station_id'] = self.user_data['station_id']
         self.json_conf['site']['ams_id'] = self.user_data['station_id']
         needs_setup = 1
      else:
         self.station_id = self.json_conf['site']['ams_id']
         print("Station ID:", self.station_id)
         self.json_conf['site']['ams_id'] = self.station_id
      
      if needs_setup == 1:
         register_resp = self.register_station()
         print(register_resp)
         self.json_conf['register_resp'] = register_resp
         self.save_json_file("../conf/as6.json", self.json_conf)
      else:
         print("Already registered.")
      self.save_json_file("../conf/setup.json", self.user_data)

      self.check_setup_defaults()
      self.UI()
   

   def auth_station(self):
      url = self.API_URL + "?cmd=setup_device&station_id=" + self.station_id + "&pin_code=" + self.pin_code 
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      content = json.loads(content)
      return(content)

   def UI(self):
      self.retro()
      print(self.header)
      time.sleep(3)
      self.setup_defaults()
      menu = ConsoleMenu("ALLSKY OBSERVING SOFTWARE SETUP", "SELECT OPTION")
      check_install = FunctionItem("INSTALL/UPDATE PACKAGES", self.check_install )
      network_int = FunctionItem("SETUP NETWORK INTERFACES", self.network_install)
      data_disk_setup = FunctionItem("FORMAT/SETUP DATA DISK", self.data_disk_install)
      backup_disk_setup = FunctionItem("SETUP DATA-BACKUP DISK", self.backup_disk_install)
      allsky_account_setup = FunctionItem("ALLSKY NETWORK ACCOUNT SIGNUP", self.allsky_account_signup)
      register_setup = FunctionItem("REGISTER STATION", self.register_station)
      setup_dirs_and_config = FunctionItem("SETUP CONFIG", self.setup_dirs_and_config)
      #menu.append_item(allsky_account_setup)
      #menu.append_item(register_setup)
      menu.append_item(check_install)
      menu.append_item(network_int)
      menu.append_item(data_disk_setup)
      menu.append_item(setup_dirs_and_config)
      menu.show()      

   def check_setup_defaults(self):
      print("CHECK DEF")
      new_defaults = ""
      if self.cfe("/home/ams/amscams/pipeline/lib/DEFAULTS.py") == 0:
         fp = open("/home/ams/amscams/pipeline/lib/DEFAULTS.py.default")
         for line in fp:
            new_defaults += line
         new_defaults = new_defaults.replace("AMSXXX", self.station_id)
         fpout = open("/home/ams/amscams/pipeline/lib/DEFAULTS.py", "w")
         fpout.write(new_defaults)
         fpout.close()
         os.system("chown -R ams:ams /home/ams/amscams/*")
         print("WROTE DEFAULTS.")
            

   def save_setup(self):
      for item in self.user_data:
         print("SAVE:", item)
      self.save_json_file(self.setup_file, self.user_data)
      input("Saved setup config. Press [ENTER] to continue.")

   def allsky_account_signup(self):
      print("ALLSKY NETWORK ACCOUNT SIGNUP")
      print("To register your station(s) you must first have an ALLSKY NETWORK ACCOUNT. ")
      print("Answer these questions to complete the process.")
      Screen().input("Press [ENTER] to continue.")

      new_allsky = self.setup_allsky_account()

   def data_disk_install(self):
      Screen().input("DATA DISK MANAGER. [ENTER] TO CONTINUE.")
      confirm = input("Do you want to format data drive (all data will be lost!) Must type YES.")
      if confirm == "YES":
         output = subprocess.check_output("lsblk | grep sd ", shell=True).decode("utf-8")
         #Filesystem                 Size  Used Avail Use% Mounted on
         try:
            output += subprocess.check_output("lsblk | grep nvm ", shell=True).decode("utf-8")
            for line in output.split("\n"):
               print(line)
         except:
            nvm = False
         drive = input("Enter the drive label (sdX) to format. Should be the large size drive!")
         cmd = "sudo mkfs -t ext4 /dev/" + drive
         print(cmd)
         confirm = input("are you sure you ant to run this command? (last chance to quit.) confirm YES spelled out. ")
         if confirm == "YES":
            print("Formatting drive...")
            os.system(cmd)
            input("Press [ENTER] to continue")
            output = subprocess.check_output("blkid | grep " + drive , shell=True).decode("utf-8")
            if drive in output:
               print("Drive added.")
               print(output)
               el = output.split("\"")
               uuid = el[1]
               fstab = "UUID=" + uuid + " /mnt/ams2               ext4    errors=continue 0       1"
               print("**** ADD THIS LINE TO /etc/fstab ****")
               cmd = "cat /etc/fstab |grep -v ams2 > temp-fstab"
               print(cmd)
               os.system(cmd)

               cmd = "echo '" + fstab + "' >> ./temp-fstab"
               print(cmd)
               os.system(cmd)

               cmd = "mv ./temp-fstab /etc/fstab " 
               os.system(cmd)
               print("Updated fstab, remounting drives.\n")
               os.system("mount -a")
               print("SHOWING ALL DRIVES. (You should see /mnt/ams2 in the list)")
               os.system("df -h")
               print("")

         else:
            print("Aborted. Should have typed YES")


      else:
         print("Aborted")

      os.system("mount -av")
      if os.path.exists("/mnt/ams2") is False:
         os.makedirs("/mnt/ams2")
      os.system("chown -R ams:ams /mnt/ams2")

      print("Completed disk format [ENTER] to continue..")
      input()

   def setup_as6_conf(self):
      #ams_id = input("Enter the AMS ID for this install. (AMSX)")
      #cam6_or7 = input("Is this a cam6 or cam7 install? (6 or 7)")
      cam6_or7 = 7
      if len(self.station_id) == 6:
         starting_cams_id = "01" + self.station_id + "1"
      if len(self.station_id) == 5:
         starting_cams_id = "01" + self.station_id + "01"
      if len(self.station_id) == 4:
         starting_cams_id = "01" + self.station_id + "001"
      starting_cams_id = int(starting_cams_id.replace("AMS", ""))
      print("Note you can change this information later in the admin, so don't worry about perfect values or mistakes.")
      operator_name = input("Enter Operator Name: ")
      operator_email = input("Enter Operator Email: ")
      operator_city = input("Enter Operator City: ")
      operator_state = input("Enter Operator State (or Region): ")
      operator_country = input("Enter Operator Country: ")
      obs_name = input("Enter Operator Observatory Name: ")
      device_lat = input("Enter Device Lat as decimal: ")
      device_lon = input("Enter Device Lon as decimal (west use negative - ): ")
      device_alt = input("Enter Device Altitude above sea level in meters: ")
      pwd = input("Enter Operator Password (for station web admin): ")

      #json_conf = load_json_file("/home/ams/amscams/conf/as6.json.default")

      self.json_conf['flask_admin'] = 1
      self.json_conf['cloud_dir'] = "/mnt/archive.allsky.tv"
      self.json_conf['cloud_latest'] = 1
      self.json_conf['dynamodb'] = {}
      self.json_conf['site']['API_HOST'] = "52.27.42.7"
      self.json_conf['site']['api_key'] = "123"
      self.json_conf['site']['pwd'] = pwd
      self.json_conf['site']['ams_id'] = self.station_id
      self.json_conf['site']['operator_name'] = operator_name
      self.json_conf['site']['operator_email'] = operator_email
      self.json_conf['site']['operator_city'] = operator_city
      self.json_conf['site']['operator_state'] = operator_state
      self.json_conf['site']['operator_country'] = operator_country
      self.json_conf['site']['obs_name'] = obs_name
      self.json_conf['site']['device_lat'] = device_lat
      self.json_conf['site']['device_lng'] = device_lon
      self.json_conf['site']['device_alt'] = device_alt
      self.json_conf['site']['cal_dir'] = "/mnt/ams2/cal/" 
      self.json_conf['site']['sd_video_dir'] = "/mnt/ams2/SD/" 
      self.json_conf['site']['hd_video_dir'] = "/mnt/ams2/HD/" 
      self.json_conf['site']['cams_queue_dir'] = "/mnt/ams2/CAMS/queue/"
      self.json_conf['site']['cams_pwd'] = "" 
      self.json_conf['site']['cams_dir'] = "/home/ams/amscams/" 
      self.json_conf['site']['mac_addr'] = ""
      self.json_conf['camera_settingsv1'] = {}
      os.system("echo " + self.station_id + " > /etc/hostname")
      cameras = {}
      cam_start = int(starting_cams_id)
      total_cams = int(cam6_or7)
      cc = 1
      for cams_id in range(cam_start, cam_start + total_cams):
         cam_id = '{:06d}'.format(cams_id)
         print(cam_id)
         ip_id = 70 + cc
         cam_ip = "192.168.76." + str(ip_id)
         key = "cam" + str(cc)
         cameras[key] = {}
         cameras[key]['cams_id'] = cam_id
         cameras[key]['cam_version'] = "2"
         cameras[key]['ip'] = cam_ip
         cameras[key]['sd_url'] = "/user=admin&password=&channel=1&stream=1.sdp"
         cameras[key]['hd_url'] = "/user=admin&password=&channel=1&stream=0.sdp"
         cameras[key]['masks'] = {}
         cameras[key]['masks']['mask0'] = "0,0,0,0"
         cameras[key]['hd_masks'] = {}
         cameras[key]['hd_masks']['hd_mask0'] = "0,0,0,0"
         cc += 1
         #if self.cfe("/home/ams/amscams/conf/mask-" + cam_id + ".txt") == 0:
         #   os.system("echo '0,0,0,0' > /home/ams/amscams/conf/mask-" + cam_id + ".txt")

      self.json_conf['cameras'] = cameras
      save_file = input("Do you want to save the conf file? [Y]")
      if save_file == "Y" or save_file == "y" or "Y" in save_file or "y" in save_file:
         self.save_json_file("/home/ams/amscams/conf/as6.json", self.json_conf)
         print("conf file saved.")

   def setup_defaults(self):
      defaults_file_temp = "/home/ams/amscams/pipeline/lib/DEFAULTS.py.default"
      defaults_file = "/home/ams/amscams/pipeline/lib/DEFAULTS.py"
      blob = ""
      fp = open(defaults_file_temp)
      for line in fp:
         blob += line
      blob = blob.replace("AMSXXX", self.station_id)
      out = open(defaults_file, "w")
      out.write(blob)
      out.close()
      print("SAVED:", defaults_file)

   def setup_dirs_and_config(self):
      # install crons
      self.setup_as6_conf()
      if "proc_dir" not in self.json_conf['site']:
         self.json_conf['site']['proc_dir'] = "/mnt/ams2/SD/proc2/"
         self.save_json_file("../conf/as6.json", self.json_conf) 
      if "camera_settingsv1" not in self.json_conf['site']:
         self.json_conf['camera_settingsv1'] = {}
      ams_id = self.station_id
      if self.cfe("/mnt/ams2",1) == 0:
         os.makedirs("/mnt/ams2")
      if self.cfe("/mnt/ams2/logs",1) == 0:
         os.makedirs("/mnt/ams2/logs")
      if self.cfe("/mnt/ams2/backup",1) == 0:
         os.makedirs("/mnt/ams2/backup")
      if self.cfe("/mnt/ams2/SD",1) == 0:
         os.makedirs("/mnt/ams2/SD")
      if self.cfe("/mnt/ams2/latest",1) == 0:
         os.makedirs("/mnt/ams2/latest")
      if self.cfe("/mnt/ams2/SD/proc2",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2")
      if self.cfe("/mnt/ams2/SD/proc2/daytime",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2/daytime")
      if self.cfe("/mnt/ams2/SD/proc2/json",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2/json")
      if self.cfe("/mnt/ams2/HD",1) == 0:
         os.makedirs("/mnt/ams2/HD")
      if self.cfe("/mnt/ams2/trash",1) == 0:
         os.makedirs("/mnt/ams2/trash")
      if self.cfe("/mnt/ams2/temp",1) == 0:
         os.makedirs("/mnt/ams2/temp")
      if self.cfe("/mnt/ams2/CAMS",1) == 0:
         os.makedirs("/mnt/ams2/CAMS")
      if self.cfe("/mnt/ams2/CAMS/queue",1) == 0:
         os.makedirs("/mnt/ams2/CAMS/queue")
      if self.cfe("/mnt/ams2/CACHE/",1) == 0:
         os.makedirs("/mnt/ams2/CACHE")
      if self.cfe("/mnt/ams2/meteor_archive/",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id ,1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id)
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/METEOR",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/METEOR")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/CAL",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/CAL")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS/MI")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS/PREVIEW")
      if self.cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA")
      print("MK2")
      #if self.cfe("/mnt/archive.allsky.tv/", 1) == 0:
      #   os.makedirs("/mnt/archive.allsky.tv")

      if self.cfe("/mnt/ams2/cal/",1) == 0:
         os.makedirs("/mnt/ams2/cal")
      if self.cfe("/mnt/ams2/cal/hd_images",1) == 0:
         os.makedirs("/mnt/ams2/cal/hd_images")
      if self.cfe("/mnt/ams2/cal/freecal",1) == 0:
         os.makedirs("/mnt/ams2/cal/freecal")
      if self.cfe("/mnt/ams2/meteors",1) == 0:
         os.makedirs("/mnt/ams2/meteors")
      if self.cfe("/mnt/ams2/latest",1) == 0:
         os.makedirs("/mnt/ams2/latest")
      if self.cfe("/home/ams/tmpvids",1) == 0:
         os.makedirs("/home/ams/tmpvids")
      print("MK3")
      #os.system("chown -R " + USER + ":" + GROUP  + " /mnt/ams2")
      #os.system("chown -R " + USER + ":" + GROUP  + " /home/ams/tmpvids")
      #os.system("chown -R " + USER + ":" + GROUP  + " /mnt/archive.allsky.tv")
      print("Make index")
      os.system("cd /home/ams/amscams/pythonv2; ./batchJobs.py fi")
      os.system("cd /home/ams/amscams/pythonv2; python3 Create_Archive_Index.py 2020 ")
      os.system("umount /mnt/archive.allsky.tv")
      os.system("chown -R ams /mnt/ams2")
      os.system("chown -R ams /home/ams")
      os.system("chown -R ams /mnt/archive.allsky.tv")

      print("FINISHED MAKING DATA DIRS.")
      Screen().input("Press [ENTER] to continue.")
      os.system("./update-cron.sh")
      os.system("./update-flask-assets.sh")
      input("[ENTER] to continue")

   def backup_disk_install(self):
      Screen().input("DATA DISK MANAGER. [ENTER] TO CONTINUE")


   def register_station(self ):
      print("REGISTER/SETUP STATION")

      if self.station_id is None:
         self.station_id = Screen().input("ENTER THE AMS ID ASSIGNED TO YOUR STATION.")
      if self.pin_code is None:
         self.pin_code = Screen().input("ENTER THE PIN CODE GIVEN TO YOU WITH YOUR AMS ID.")
      print("AMS ID:", self.station_id)
      print("PIN CODE:", self.pin_code)
      resp = self.auth_station()
      if (resp['msg']) != "Station PIN Matched":
         input("Register Station Failed. Please try again or contact support.")
         exit()
      else:
         if "username" not in resp['station_data']:
            new_allsky = 1
         elif resp['station_data']['username'] == "unclaimed":
            new_allsky = 1
         else:
            new_allsky = 0
         #if new_allsky == 1:
         #   new_allsky = self.setup_allsky_account()
 
         print("Register Message:", resp['msg'])
      return(resp) 

         #print("Current Station Data:" )
         #for key in resp['station_data']:
         #   if key != 'cameras' and key != 'monitor' and key != 'registration':         
         #      print(key, resp['station_data'][key])
         #print("NEW ALLSKY SETUP? ", new_allsky, resp['station_data']['username']) 
         #input("Review current station info. If it is incomplete or incorrect update it in the web admin config area.")
      
   def setup_allsky_account(self):
      print("ALLSKY NETWORK ACCOUNT SETUP") 
      choice = "1"
      if len(self.user_data) > 0:
         print("DATA FROM PREVIOUS SESSION IS SAVED.")
         for key in self.user_data:
            print(key, self.user_data[key])
         if "submit_status" not in self.user_data:
            print("This data has not been submitted yet.")
            choice = input("Press [1] to edit the data or [2] to submit it for registration.")

      if choice == "1":      
         print("Enter a username to identify yourself on the network and use as a login for all stations and restricted areas of the network. For example: jsmith ") 
         self.user_data['username'] = input("ALLSKY NETWORK USERNAME:")
         print("Enter a strong password to use for your account.") 
         self.user_data['password'] = input("ALLSKY NETWORK PASSWORD:")
         self.user_data['email'] = input("YOUR EMAIL")
         self.user_data['phone_number'] = input("YOUR CELL PHONE INCLUDING COUNTRY CODE STARTING WITH +")
         self.user_data['operator_name'] = input("YOUR FULL NAME (FOR PHOTO CREDITS)")
         self.save_setup()
      else:
         print("Submitting account setup data to ALLSKY NETWORK CLOUD.")
         self.submit_allsky_account_signup()
         input("Press [ENTER] to continue")

   def submit_allsky_account_signup(self):
      if "username" not in self.user_data:
         self.user_data['username'] = "unclaimed"   
      if "password" not in self.user_data:
         self.user_data['password'] = "unclaimed"   
      if "operator_name" not in self.user_data:
         self.user_data['operator_name'] = ""   
      if "email" not in self.user_data:
         self.user_data['email'] = ""   
      if "phone_number" not in self.user_data:
         self.user_data['phone_number'] = ""   
      api_url = "https://www.allsky.tv/app/API/" + self.user_data['username'] + "/submit_signup"
      if "station_id" not in self.user_data:
         self.user_data['station_id'] = ""
      method = "POST"
      data = {
         'username': self.user_data['username'],
         'password': self.user_data['password'],
         'name':  self.user_data['operator_name'],
         'station_id': self.user_data['station_id'],
         'email': self.user_data['email'],
         'phone_number': self.user_data['phone_number'],
         'terms': "0"
      }
      print("SUB MIT DATA:", data)
      headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
      response = requests.post(api_url, data=json.dumps(data) , headers=headers)
      print(response.content.decode())
      input()


   def network_install(self):
      import psutil
      temp = psutil.net_if_addrs()
      wired_interfaces = []
      wifi_interfaces = []
      os.system("clear")

      print("Wired interfaces on this PC.")
      for tt in temp:
         if "lo" not in tt and "w" not in tt:
            wired_interfaces.append(tt)
         if "w" in tt:
            wifi_interfaces.append(tt)

      c = 1
      lookup = {}
      nums = []

      NETPLAN = """
network:
  version: 2
  renderer: NetworkManager
  ethernets:
 """


      for i in sorted(wired_interfaces):
         ni.ifaddresses(i)
         try:
            ip = ni.ifaddresses(i)[ni.AF_INET][0]['addr']
         except:
            ip = None
         print(c, ") WIRED:", i, ip)
         lookup[str(c)] = i
         nums.append(c)
         c += 1

      options = str(nums)
      cams_ind = input("Select the wired interface to use with the cameras." + options)
      cams_interface = lookup[cams_ind]

      for i in sorted(wired_interfaces):
         if i != cams_interface:
            NETPLAN += """
     {:s}:
        dhcp4: true
        optional: true
        """.format(i)

         else:
            NETPLAN += """
     {:s}:
        addresses: [192.168.76.1/24]
        nameservers:
           addresses: [8.8.8.8,8.8.4.4]
        optional: true """.format(cams_interface)


      wifi_yn = input("Do you want to setup the wifi interface?")
      if wifi_yn == "Y" or wifi_yn == "y":

         wifi_ssid = input("Enter wifi SSID: ")
         wifi_pwd= input("Enter wifi Pass: ")
         NETPLAN += """
  wifis:
     {:s}:
        dhcp4: yes 
        access-points:
           "{:s}":
              password: "{:s}" """.format(wifi_interfaces[0], wifi_ssid, wifi_pwd)


      print("NETPLAN FILE WILL BE:")
      print(NETPLAN)
      
      confirm2 = input("Apply changes to netplan config files? " + self.NETPLAN_FILE + " (Y/N)")
      if confirm2 == "Y" or confirm2 == "y":
         netout = open(self.NETPLAN_FILE,"w")
         netout.write(NETPLAN)
         netout.close()
         os.system("netplan apply")
      else:
         print("The netplan file was NOT saved.")

      Screen().input("We are done. [ENTER] to continue.")

    


      for i in sorted(wifi_interfaces):
         ni.ifaddresses(i)
         try:
            ip = ni.ifaddresses(i)[ni.AF_INET][0]['addr']
         except:
            ip = None
         #print(c, "WIFI", i, ip)
         #c += 1
      exit()

   def network_install_old(self):
      import psutil
      temp = psutil.net_if_addrs()
      interfaces = []
      alts = {}
      for i in temp:
         interfaces.append(i)
         if "wlo" in i:
            print("WLO FOUND!")
            os.system("ip a |grep altname > tmp.txt")
            fp = open("tmp.txt")
            for line in fp:
               alt = line.replace("altname", "")
               alt = alt.replace(" ", "")
               alt = alt.replace("\n", "")
               alts[i] = alt

      #print(interfaces)
      #interfaces = os.listdir("/sys/class/net/") 
      ints = []
      for i in interfaces:
         print(i)
         if i != "lo" and ("eth" in i or "en" in i or "wl" in i) :
            ni.ifaddresses(i)
            try:
               ip = ni.ifaddresses(i)[ni.AF_INET][0]['addr']
            except:
               ip = None
            if ip is not None:
               if "192.168.76.1" in ip: 
                  ntype = "CAMS_ETH"
               else: 
                  ntype = "NETWORK_ETH"
            else:
               ntype = "LINK DOWN"
            if "w" in i :
               ntype = "WIFI"
               wifi_interface = i
               if i in alts:
                  wifi_interface = alts[i]

            ints.append((i, ip,ntype))
      c = 1
      for row in ints:
         (interface, ip, ntype) = row
         if "wlo" in interface :
            interface = alts[interface]
         print(str(c) + ")", interface, ip, ntype)
         c += 1
      net_i= input("Select the interface to use for the internet. (It should have an IP address already that matches your network.)")
      cams_i = input("Select the interface to use for the cameras")
      network_interface = ints[int(net_i)-1][0]
      cams_interface = ints[int(cams_i)-1][0]
      wifi = "No"

      self.NETPLAN = self.NETPLAN.replace("INT_NET", network_interface)
      self.NETPLAN = self.NETPLAN.replace("INT_CAMS", cams_interface)

      if "w" in network_interface:
         print("You selected a wifi interface to connect to the internet.")
         net_i = input("Select the WIRED ethernet interface that will not be used: ")
         network_interface = ints[int(net_i)-1][0]

         if "wlo" in network_interface :
            network_interface = alts[network_interface]

         wifi_ssid = input("Enter the WIFI SSID: ")
         wifi_pass = input("Enter the WIFI Password: ")
         wifi = "Yes"



      if wifi == "Yes":
         print("WIFI INTERFACE IS:", wifi_interface)
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("INT_WIFI", wifi_interface)
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("WIFI_SSID", wifi_ssid)
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("WIFI_PASS", wifi_pass)

         self.NETPLAN += self.NETPLAN_WIFI

      print("This is your network setup configuration:")
      print("Network Interface:", network_interface)
      print("Cams Interface:", cams_interface)
      print("Using WIFI:", wifi)
      if wifi == "Yes":
         print("WIFI SSID:", wifi_ssid)
         print("WIFI PASSWD:", wifi_pass)
      confirm = input("Does this look correct? (Y/N)")
      print("REVIEW THE NETPLAN FILE!")
      print("-----------------------!")
      print(self.NETPLAN)
      confirm2 = input("Apply changes to netplan config files? " + self.NETPLAN_FILE + " (Y/N)")
      if confirm2 == "Y" or confirm2 == "y":
         netout = open(self.NETPLAN_FILE,"w")
         netout.write(self.NETPLAN)
         netout.close()
         os.system("netplan apply")
      Screen().input("We are done. [ENTER] to continue.")

   def load_pip_packages(self):
      self.pip_list = []
      fp = open("pip.conf")
      for line in fp:
         if line[0] != "#":
            line = line.replace("\n","")
            self.pip_list.append(line)

   def load_apt_packages(self):
      self.apt_list = []
      fp = open("apt.conf")
      for line in fp:
         if line[0] != "#":
            line = line.replace("\n", "")
            self.apt_list.append(line)

   def load_custom_packages(self):
      self.custom_list = []
      fp = open("custom.conf")
      for line in fp:
         if line[0] != "#":
            line = line.replace("\n", "")
            self.custom_list.append(line)

   def check_install(self ):
      print("check_install")
      all_cmds = ""
      self.load_apt_packages()
      self.load_pip_packages()
      self.load_custom_packages()
      Screen().input("This program will check all system dependencies and install those that are missing. Press [ENTER] to continue.")
      cmd = "apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages update"
      print(cmd)
      os.system(cmd)
      # install/update apt packages 
      oneline = "apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install " 
      for apt in self.apt_list:
         cmd = "apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install " + apt + " " 
         oneline += apt + " " 
         print(cmd)
         os.system(cmd)
         all_cmds += cmd + "\n"

      oneline += "\n"
      oneline += "python3 -m pip install --upgrade " 
      if os.path.exists("/usr/bin/pip3") is False:
         # pip not installed!
         os.system("./install-pip.sh")
      # install/update pip packages 
      for pip in self.pip_list:
         cmd = "python3 -m pip install --upgrade " + pip
         print(cmd)
         oneline += pip + " " 
         os.system(cmd)
         all_cmds += cmd + "\n"

      for cust in self.custom_list:
         cmd = cust
         print(cmd)
         os.system(cmd)
         all_cmds += cmd + "\n"


      out = open("oneline-cmds.sh", "w")
      #out.write(all_cmds)
      out.write(oneline)
      out.close()

      out = open("install-cmds.sh", "w")
      out.write(all_cmds)
      out.close()

      Screen().input("We are done. [ENTER] to continue.")

   def retro(self):
      os.system("clear")
      self.header = """
  ____  _      _      _____ __  _  __ __
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/
** O B S E R V I N G   S O F T W A R E **

AllSky.com/ALLSKY7 - (C) Mike Hankey LLC 2016-2022
Licensed use permitted. Terms and conditions apply.

Loading...
      """

   def load_json_file(self, json_file):
      #try:
      if True:
         with open(json_file, 'r' ) as infile:
            json_data = json.load(infile)
      #except:
      #   json_data = False
      return json_data

   def save_json_file(self,json_file, json_data, compress=False):
      if "cp" in json_data:
         for key in json_data['cp']:
            if type(json_data['cp'][key]) == np.ndarray:
               json_data['cp'][key] = json_data['cp'][key].tolist()
      with open(json_file, 'w') as outfile:
         if(compress==False):
            json.dump(json_data, outfile, indent=4, allow_nan=True )
         else:
            json.dump(json_data, outfile, allow_nan=True)
      outfile.close()

   def cfe(self,file,dir = 0):
      if dir == 0:
         file_exists = Path(file)
         if file_exists.is_file() is True:
            return(1)
         else:
            return(0)
      if dir == 1:
         file_exists = Path(file)
         if file_exists.is_dir() is True:
            return(1)
         else:
            return(0)

NETPLAN_FILE = "/etc/netplan/00-installer-config.yaml"
if os.path.isfile("/home/ams/netplan.backup") == 0 and os.path.isfile("/etc/netplan/00-installer-config.yaml") == 0:
   os.system("cp " + NETPLAN_FILE + " /home/ams/netplan.backup")

        #routes:
        #   - to: 0.0.0.0/0
        #     via: 192.168.1.1
        #     metric: 100

NETPLAN = """
network:
  version: 2
  renderer: NetworkManager
  ethernets:
     INT_NET:
        dhcp4: true
        optional: true
     INT_CAMS:
        addresses: [192.168.76.1/24]
        nameservers:
           addresses: [8.8.8.8,8.8.4.4]
        optional: true
"""
NETPLAN_WIFI = """
  wifis:
     INT_WIFI:
        dhcp4: yes 
        access-points:
           "WIFI_SSID":
              password: "WIFI_PASS"
"""

S = AS7Setup()
S.NETPLAN = NETPLAN
S.NETPLAN_WIFI = NETPLAN_WIFI
S.NETPLAN_FILE = NETPLAN_FILE


S.start_up()
exit()
S.UI()
