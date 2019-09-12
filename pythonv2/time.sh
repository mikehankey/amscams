echo "BEFORE SYNC TIME:"
date
service ntp stop
ntpdate pool.ntp.org 
service ntp start
echo "AFTER SYNC TIME:"
date
