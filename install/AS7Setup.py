#!/usr/bin/python3
import requests
import json
from pathlib import Path
import os
try:
   from consolemenu import *
   from consolemenu.items import *
except:
   os.system("pip3 install consolemenu")
   os.system("pip3 install console-menu")
   from consolemenu import *
   from consolemenu.items import *

import getpass
import netifaces as ni

class AS7Setup():

   def __init__(self):
      username = getpass.getuser()
      self.setup_file = "/home/ams/amscams/conf/setup.json"
      if self.cfe(self.setup_file) == 1:
         self.user_data = self.load_json_file(self.setup_file)
      else:
         self.user_data = {}
      print(username)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      if username != "root":
         print("""THIS SCRIPT MUST BE RUN AS ROOT! use "sudo"
         sudo python3 AS7Setup.py
         """)
         os.system("sudo python3 AS7Setup.py")

         exit()
      if self.cfe("setup.json") == 0:
         self.setup_data = {}
      else:
         self.setup_data = self.load_json_file("setup.json")

   def auth_station(self):
      url = self.API_URL + "?cmd=setup_device&station_id=" + self.station_id + "&pin_code=" + self.pin_code 
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      content = json.loads(content)
      return(content)

   def UI(self):
      menu = ConsoleMenu("ALLSKY OBSERVING SOFTWARE - INSTALLER AND SETUP ", "SELECT OPTION")
      check_install = FunctionItem("INSTALL/UPDATE PACKAGES", self.check_install )
      network_int = FunctionItem("SETUP NETWORK INTERFACES", self.network_install)
      data_disk_setup = FunctionItem("FORMAT/SETUP DATA DISK", self.data_disk_install)
      backup_disk_setup = FunctionItem("SETUP DATA-BACKUP DISK", self.backup_disk_install)
      allsky_account_setup = FunctionItem("ALLSKY NETWORK ACCOUNT SIGNUP", self.allsky_account_signup)
      register_setup = FunctionItem("REGISTER STATION", self.register_station)
      menu.append_item(allsky_account_setup)
      menu.append_item(register_setup)
      menu.append_item(check_install)
      menu.append_item(network_int)
      menu.append_item(data_disk_setup)
      menu.show()      

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
      Screen().input("DATA DISK MANAGER.")

   def backup_disk_install(self):
      Screen().input("DATA DISK MANAGER.")

   def register_station(self):
      print("REGISTER/SETUP STATION")
      self.station_id = Screen().input("ENTER THE AMS ID ASSIGNED TO YOUR STATION.")
      self.pin_code = Screen().input("ENTER THE PIN CODE GIVEN TO YOU WITH YOUR AMS ID.")
      print("AMS ID:", self.station_id)
      print("PIN CODE:", self.pin_code)
      resp = self.auth_station()
      if (resp['msg']) != "Station PIN Matched":
         input("Register Station Failed. Please try again or contact support.")
         return()
      else:
         if "username" not in resp['station_data']:
            new_allsky = 1
         elif resp['station_data']['username'] == "unclaimed":
            new_allsky = 1
         else:
            new_allsky = 0
         if new_allsky == 1:
            new_allsky = self.setup_allsky_account()
 
         print("Register Message:", resp['msg'])
         print("Current Station Data:" )
         for key in resp['station_data']:
            if key != 'cameras' and key != 'monitor' and key != 'registration':         
               print(key, resp['station_data'][key])
         print("NEW ALLSKY SETUP? ", new_allsky, resp['station_data']['username']) 
         input("Review current station info. If it is incomplete or incorrect update it in the web admin config area.")

   def setup_allsky_account(self):
      print("ALLSKY NETWORK ACCOUNT SETUP") 
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
      interfaces = os.listdir("/sys/class/net/") 
      ints = []
      for i in interfaces:
         if i != "lo" :
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
            ints.append((i, ip,ntype))
      c = 1
      for row in ints:
         (interface, ip, ntype) = row
         print(str(c) + ")", interface, ip, ntype)
         c += 1
      net_i= input("Select the interface to use for the internet.")
      cams_i = input("Select the interface to use for the cameras")
      network_interface = ints[int(net_i)-1][0]
      cams_interface = ints[int(cams_i)-1][0]
      wifi = "No"

      if "w" in network_interface:
         print("You selected a wifi interface to connect to the internet.")
         net_i = input("First, select the WIRED ethernet interface that will not be used.")
         network_interface = ints[int(net_i)-1][0]
         wifi_ssid = input("Enter the WIFI SSID")
         wifi_pass = input("Enter the WIFI Password")
         wifi = "Yes"

      if wifi == "Yes":
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("INT_WIFI", wifi_interface)
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("WIFI_SSID", wifi_ssid)
         self.NETPLAN_WIFI = self.NETPLAN_WIFI.replace("WIFI_PASS", wifi_pass)

      self.NETPLAN = self.NETPLAN.replace("INT_NET", network_interface)
      self.NETPLAN = self.NETPLAN.replace("INT_CAMS", cams_interface)
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
      oneline += "pip3 install --upgrade " 
      # install/update pip packages 
      for pip in self.pip_list:
         cmd = "pip3 install --upgrade " + pip
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
os.system("cp " + NETPLAN_FILE + "~")
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
        routes:
           - to: 0.0.0.0/0
             via: 192.168.1.1
             metric: 100
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
S.UI()
