# commands that will auto run on new boot. 
# should start up the uwsgi (ssl or none)
# mount wasabi
# check disk
# git pull
/bin/date >> /home/ams/reboot.log

sudo timedatectl set-timezone UTC

runuser -l  ams -c 'cd /home/ams/amscams/; git pull'
runuser -l  ams -c 'cd /home/ams/amscams/pythonv2/; ./wasabi.py mnt '
runuser -l  ams -c 'cd /home/ams/amscams/pythonv2/; ./doDay.py cd'

cd /home/ams/amscams/install; ./check_install.py

sudo systemctl start cron
sudo systemctl enable cron


#@
