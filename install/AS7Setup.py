#!/usr/bin/python3
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
      print(username)
      if username != "root":
         print("""THIS SCRIPT MUST BE RUN AS ROOT! use "sudo"
         sudo python3 AS7Setup.py
         """)
         exit()
      if self.cfe("setup.json") == 0:
         self.setup_data = {}
      else:
         self.setup_data = self.load_json_file("setup.json")

   def UI(self):
      menu = ConsoleMenu("ALLSKY OBSERVING SOFTWARE - INSTALLER AND SETUP ", "SELECT OPTION")
      check_install = FunctionItem("INSTALL/UPDATE PACKAGES", self.check_install )
      network_int = FunctionItem("SETUP NETWORK INTERFACES", self.network_install)
      data_disk_setup = FunctionItem("FORMAT/SETUP DATA DISK", self.data_disk_install)
      backup_disk_setup = FunctionItem("SETUP DATA-BACKUP DISK", self.backup_disk_install)
      register_setup = FunctionItem("REGISTER STATION", self.register_station)
      menu.append_item(register_setup)
      menu.append_item(check_install)
      menu.append_item(network_int)
      menu.append_item(data_disk_setup)
      menu.show()      

   def data_disk_install(self):
      Screen().input("DATA DISK MANAGER.")

   def backup_disk_install(self):
      Screen().input("DATA DISK MANAGER.")

   def register_station(self):
      print("REGISTER/SETUP STATION")
      ams_id = Screen().input("ENTER THE AMS ID ASSIGNED TO YOUR STATION.")
      pin_code = Screen().input("ENTER THE PIN CODE GIVEN TO YOU WITH YOUR AMS ID.")
      print("AMS ID:", ams_id)
      print("PIN CODE:", pin_code)
      input("Press enter to continue")

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
