from dvrip import DVRIPCam
from time import sleep
import sys
import json
import argparse

parser = argparse.ArgumentParser(description='IpCam Admin.')
parser.add_argument('cmd', type=str, help='Main command')
parser.add_argument('-i', '--ip', type=str, default='ip', help='cam ip')
parser.add_argument('-c', '--cam_num', type=str, default='cam_num', help='cam_num (1-8)')
parser.add_argument('-p', '--password', type=str, default='password', help='password')
args = parser.parse_args()

# get current user/pass
data = json.load(open('/home/ams/amscams/conf/as6.json'))
for cam in data['cameras']:
    if cam == args.cam_num:
        print(cam)
        camera_ip = data['cameras'][cam]['ip']
        url = data['cameras'][cam]['sd_url']
        host_ip = data['cameras'][cam]['ip']
        el = url.split("?")[-1].split("&")
        for e in el:
            k,v = e.split("=")
            if k == "password":
                current_password = v
        print("Current password:", current_password)

cam = DVRIPCam(host_ip, user='admin', password=current_password)
if cam.login():
	print("Success! Connected to " + host_ip)
else:
	print("Failure. Could not connect.")

print("Camera time:", cam.get_time())

# Reboot camera
#cam.reboot()
#sleep(60) # wait while camera starts

# Login again
#cam.login()
# Sync camera time with PC time
cam.set_time()

# get general info
#params = cam.get_general_info()
#print(json.dumps(params, indent=4))

# get system info
#params = cam.get_system_info()
#print(json.dumps(params, indent=4))

#params = cam.get_system_capabilities()
#print(json.dumps(params, indent=4))

#params = cam.get_info("Camera")
#print(json.dumps(params, indent=4))

#change pass for admin
#User "test2" with pssword "123123"

cam.changePasswd(args.password,cam.sofia_hash(current_password),"admin")
print("new password", args.password)

# Disconnect
cam.close()
