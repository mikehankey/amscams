# use this command to mount the allsky data drive to another PC with samba. 
#xx
# NOTE! Samba server must be installed and configured on the AllSky PC before this will work.  (it is not setup by default)
# 
sudo mount -t drvfs '\\192.168.1.4\Public' /mnt/ams2 -o noperm,user=ams,pass=xrp23q,uid=1001,gid=0,file_mode=0777,dir_mode=0777

#mount -t cifs //ams1:/Public /mnt/ams2 -o noperm,user=ams,pass=xrp23q,uid=1001,gid=0,file_mode=0777,dir_mode=0777

#mount -t cifs //192.168.1.4/Public /mnt/ams2 -o noperm,user=ams,pass=xrp23q,uid=1001,gid=0,file_mode=0777,dir_mode=0777

