#!/usr/bin/python3

"""
 - should be run after the initial depencies are installed 


"""
import subprocess
import json
import os
import sys
from pathlib import Path
USER = "ams"
GROUP = "ams"
#USER = "meteorcam"
#GROUP = "pi"

def format_drive():
   confirm = input("Do you want to format data drive (all data will be lost!) Must type YES.")
   if confirm == "YES":
      output = subprocess.check_output("lsblk | grep sd ", shell=True).decode("utf-8")
      #Filesystem                 Size  Used Avail Use% Mounted on

      for line in output.split("\n"):
         print(line)   
      drive = input("Enter the drive label (sdX) to format. Should be the large size drive!")
      cmd = "sudo mkfs -t ext4 /dev/" + drive
      print(cmd)
      confirm = input("are you sure you ant to run this command? (last chance to quit.)")
      if confirm == "YES":
         print("Formatting drive...")
         #os.system(cmd)
         output = subprocess.check_output("blkid | grep " + drive , shell=True).decode("utf-8")
         if drive in output:
            print("Drive added.")
            print(output)
            el = output.split("\"")
            uuid = el[1]
            fstab = "UUID=" + uuid + " /mnt/ams2               ext4    errors=continue 0       1\n"
            print(fstab)
      else:
         print("Aborted. Should have typed YES")


   else:
      print("Aborted")

# Once the 1TB drive has been identified reformat it with linux ext4 file system
#sudo mkfs -t ext4 /dev/sda1

# mount the drive, chown and make the default dirs
#sudo mount /dev/sda1 /mnt/ams2

#sudo chown -R ams:ams /mnt/ams2
#mkdir /mnt/ams2/HD
#mkdir /mnt/ams2/SD
#mkdir /mnt/ams2/SD/proc
#mkdir /mnt/ams2/SD/proc/daytime
#mkdir /mnt/ams2/meteors/


def save_json_file(json_file, json_data, compress=False):
   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True)
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()

def load_json_file(json_file):
   with open(json_file, 'r' ) as infile:
      json_data = json.load(infile)
   return(json_data)


def cfe(file,dir = 0):
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


def get_repos():
   """ Download the fireball and amscams repos
   """
   os.system("cd /home/ams; git clone https://github.com/mikehankey/fireball_camera.git")
   os.system("cd /home/ams; git clone https://github.com/mikehankey/amscams.git")

def config_apache():
   site_file = "/etc/apache2/sites-enabled/000-default.conf"
   #site_file = "/etc/apache2/default-server.conf"
   sites_enabled = """
<Directory /var/www/html/pycgi>
Options ExecCGI FollowSymLinks
AddHandler cgi-script .py
</Directory>

<VirtualHost *:80>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html
        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>


"""
   fp = open(site_file, "w")
   fp.write(sites_enabled)
   fp.close()
   # change run user
   env_text = ""
   fp = open("/etc/apache2/envvars")
   for line in fp:
      env_text += line
   env_text = env_text.replace("www-data", "ams")
   fp.close()

   fp = open("/etc/apache2/envvars", "w")
   fp.write(env_text)
   fp.close()

   os.system("ln -s /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load")
   os.system("rm /var/www/html/index.html")

   # make default index page
   index = "<a href=/pycgi/webUI.py>Login</a>"
   fp = open("/var/www/html/index.html", "w")
   fp.write(index)
   fp.close()

   # link required files and directories
   if cfe("/var/www/html/pycgi/", 1) == 0:
      os.system("ln -s /home/ams/amscams/python/pycgi /var/www/html/pycgi")
   if cfe("/var/www/html/pycgi/webUI.py") == 0:
      os.system("ln -s /home/ams/amscams/pythonv2/webUI.py /var/www/html/pycgi")
   if cfe("/var/www/html/pycgi/dist/", 1) == 0:
      os.system("ln -s /home/ams/amscams/dist/ /var/www/html/pycgi")
   if cfe("/var/www/html/pycgi/src/", 1) == 0:
      os.system("ln -s /home/ams/amscams/src/ /var/www/html/pycgi")
   if cfe("/var/www/html/pycgi/video_player.html") == 0:
      os.system("ln -s /home/ams/amscams/python/pycgi/video_player.html /var/www/html/pycgi/video_player.html")



   os.system("/etc/init.d/apache2 restart")


def setup_network_interface():
   """ sets up the /etc/network/interfaces file for 2 LAN setup """

   ints = os.listdir("/sys/class/net/")
   print(ints)
   for interface in ints:
      if "lo" not in interface and "wlo" not in interface:
         print(interface)
         if "1" in interface or "4" in interface:
            INT01 = interface
         if "3" in interface or "2" in interface:
            INT02 = interface


   interfaces = """

# interfaces(5) file used by ifup(8) and ifdown(8)
auto lo 
iface lo inet loopback

#primary interface 
auto """ + INT01 + """

#secondary interface 
auto """ + INT02 + """
iface enp3s0 inet static
address 192.168.76.1
netmask 255.255.255.0
broadcast 192.168.76.255
network 192.168.76.0

post-up /home/ams/fireball_camera/iptables.sh


   """

   print (interfaces)
   confirm = input("Does this look right? Press Y to install or N to quit.")
   if confirm == "Y":
      fp = open("/etc/network/interfaces", "w")
      fp.write(interfaces)
   else:
      print("Skipping network interface install.")

def setup_dirs():
   ams_id = input("Enter the AMS ID for this install. (AMSX)")
   print("This should only be done after the data drive has been installed and formatted")
   do_dir = input("Do you want to create all of the data dirs? (Y) ")
   if do_dir == "Y":
      if cfe("/mnt/ams2",1) == 0:
         os.makedirs("/mnt/ams2")
      if cfe("/mnt/ams2/SD",1) == 0:
         os.makedirs("/mnt/ams2/SD")
      if cfe("/mnt/ams2/latest",1) == 0:
         os.makedirs("/mnt/ams2/latest")
      if cfe("/mnt/ams2/SD/proc2",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2")
      if cfe("/mnt/ams2/SD/proc2/daytime",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2/daytime")
      if cfe("/mnt/ams2/SD/proc2/json",1) == 0:
         os.makedirs("/mnt/ams2/SD/proc2/json")
      if cfe("/mnt/ams2/HD",1) == 0:
         os.makedirs("/mnt/ams2/HD")
      if cfe("/mnt/ams2/trash",1) == 0:
         os.makedirs("/mnt/ams2/trash")
      if cfe("/mnt/ams2/temp",1) == 0:
         os.makedirs("/mnt/ams2/temp")
      if cfe("/mnt/ams2/CAMS",1) == 0:
         os.makedirs("/mnt/ams2/CAMS")
      if cfe("/mnt/ams2/CAMS/queue",1) == 0:
         os.makedirs("/mnt/ams2/CAMS/queue")
      if cfe("/mnt/ams2/CACHE/",1) == 0:
         os.makedirs("/mnt/ams2/CACHE")
      if cfe("/mnt/ams2/meteor_archive/",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id ,1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id)
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/METEOR",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/METEOR")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/CAL",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/CAL")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS/MI")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/DETECTS/PREVIEW")
      if cfe("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA",1) == 0:
         os.makedirs("/mnt/ams2/meteor_archive/" + ams_id + "/NOAA")
      if cfe("/mnt/archive.allsky.tv/", 1) == 0:
         os.makedirs("/mnt/archive.allsky.tv")

      if cfe("/mnt/ams2/CAL/",1) == 0:
         os.makedirs("/mnt/ams2/CAL")
      if cfe("/mnt/ams2/CAL/hd_images",1) == 0:
         os.makedirs("/mnt/ams2/CAL/hd_images")
      if cfe("/mnt/ams2/CAL/freecal",1) == 0:
         os.makedirs("/mnt/ams2/CAL/freecal")
      if cfe("/mnt/ams2/meteors",1) == 0:
         os.makedirs("/mnt/ams2/meteors")
      if cfe("/mnt/ams2/latest",1) == 0:
         os.makedirs("/mnt/ams2/latest")
      if cfe("/home/ams/tmpvids",1) == 0:
         os.makedirs("/home/ams/tmpvids")
      os.system("chown -R " + USER + ":" + GROUP  + " /mnt/ams2")
      os.system("chown -R " + USER + ":" + GROUP  + " /home/ams/tmpvids")
      os.system("chown -R " + USER + ":" + GROUP  + " /mnt/archive.allsky.tv")
   
      os.system("cd /home/ams/amscams/pythonv2; ./batchJobs.py fi")
      os.system("cd /home/ams/amscams/pythonv2; python3 Create_Archive_Index.py 2020 ")


def setup_as6_conf():
   ams_id = input("Enter the AMS ID for this install. (AMSX)")
   cam6_or7 = input("Is this a cam6 or cam7 install? (6 or 7)")
   starting_cams_id = input("Enter the starting CAMS ID number (0100XX)")
   operator_name = input("Enter Operator Name")
   operator_email = input("Enter Operator Email")
   operator_city = input("Enter Operator City")
   operator_state = input("Enter Operator State (or Region)")
   operator_country = input("Enter Operator Country")
   obs_name = input("Enter Operator Observatory Name")
   device_lat = input("Enter Device Lat as decimal")
   device_lon = input("Enter Device Lon as decimal")
   device_alt = input("Enter Device Altitude above sea level in meters")
   pwd = input("Enter Operator Password")

   json_conf = load_json_file("/home/ams/amscams/conf/as6.json.default")
   json_conf['site']['API_HOST'] = "52.27.42.7"
   json_conf['site']['api_key'] = "123"
   json_conf['site']['pwd'] = pwd
   json_conf['site']['ams_id'] = ams_id
   json_conf['site']['operator_name'] = operator_name 
   json_conf['site']['operator_email'] = operator_email
   json_conf['site']['operator_city'] = operator_city
   json_conf['site']['operator_state'] = operator_state
   json_conf['site']['operator_country'] = operator_country
   json_conf['site']['obs_name'] = obs_name
   json_conf['site']['device_lat'] = device_lat
   json_conf['site']['device_lng'] = device_lon
   json_conf['site']['device_alt'] = device_alt

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
      if cfe("/home/ams/amscams/conf/mask-" + cam_id + ".txt") == 0:
         os.system("echo '0,0,0,0' > /home/ams/amscams/conf/mask-" + cam_id + ".txt")
   
   json_conf['cameras'] = cameras
   save_file = input("Do you want to save the conf file?")
   if save_file == "Y":
      save_json_file("/home/ams/amscams/conf/as6.json", json_conf) 
      print("conf file saved.")

def setup_vpn():
   url = input("Enter URL")
   pass_file = url.replace(".ovpn", ".txt")
   os.system("sudo apt-get install openvpn")
   os.system("wget " + url + " -O /etc/openvpn/as6vpn.ovpn")
   os.system("wget " + pass_file + " -O /etc/openvpn/as6vpn.txt")
   

#get_repos()
#setup_network_interface()

#config_apache()

#format_drive()
#setup_as6_conf()

#setup_dirs()
setup_vpn()
os.system("sudo chown -R ams:ams /mnt/ams2")
os.system("sudo chown -R ams:ams /home/ams")
