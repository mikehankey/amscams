"""
install latest astrometry.net and diable old version
make sure data files are in /usr/share/astrometry
disable old dir
"""
import os
import json

# Get the current user's UID
user_uid = os.getuid()

# Check if the current user is root
if user_uid != 0:
    print("Current user is not root. Aborting.")
    exit()  # Abort the program
else:
    print("Current user is root.")

need_update = False
astro_data_dir = '/usr/share/astrometry'
astro_bin_dir = '/usr/bin'
astro_old_dir = '/usr/local/astrometry'
cal_dir = '/mnt/ams2/cal'
cal_health_file = cal_dir + '/cal_health.info'

if os.path.exists(cal_health_file) is False:
    need_update = True
    cal_health = {}
else:
    cal_health = json.load(open(cal_health_file))
if "astrometry.net" not in cal_health:
    need_update = True
if os.path.exists(astro_old_dir):
    need_update = True    
if os.path.exists(astro_old_dir):
    need_update = True    
if os.path.exists(astro_bin_dir + '/solve-field') is False:
    need_update = True    
data_files = os.listdir(astro_data_dir)
if len(data_files) == 0:
    need_update = True

if need_update is False:
    print("NO UPDATE NEEDED")
    exit()

print("UPDATE NEEDED FOR ASTROMETRY.NET")

cmd = "apt-get update"
os.system(cmd)
cmd = "apt-get install astrometry.net"
os.system(cmd)

if os.path.exists(astro_old_dir) or len(data_files) == 0:
    cmd = "cp /usr/local/astrometry/data/* /usr/share/astrometry/"
    os.system(cmd)
    cmd = "mv /usr/local/astrometry /usr/share/astrometry.old"
    os.system(cmd)
