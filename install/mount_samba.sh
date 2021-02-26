# use this command to mount the allsky data drive to another PC with samba. 
# NOTE! Samba server must be installed and configured on the AllSky PC before this will work.  (it is not setup by default)
# 


mount -t cifs //192.168.1.X/Public /mnt/ams2 -o noperm,user=ams,pass=YOUR_PASSWD,uid=1001,gid=0,file_mode=0777,dir_mode=0777

