#/bin/sh
echo " "
echo "### station ###" > /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "AMS22" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** station ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### date ###" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
date -Iseconds >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** date ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### who ###" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
who -a >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** who ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### uptime ###" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
uptime >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** uptime ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### cpu ###" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
ps -aux | sort -nr -k 3 | head -10 >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** cpu ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### mem ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
ps -aux | sort -nr -k 4 | head -10 >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** mem ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### iostat ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
iostat >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** iostat ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### free ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
free -m >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** free ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### find ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
find /mnt/ams2/HD -mmin 1 -printf '%f\t%s\n' >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** find ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### df ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
df --type=ext4 >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "*** df ***" >> /mnt/archive.allsky.tv/AMS22/monitor/status.txt
echo "### end ###" >>  /mnt/archive.allsky.tv/AMS22/monitor/status.txt
