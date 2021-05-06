#/bin/sh
station="AMSXX"
main_file=/mnt/archive.allsky.tv/$station/monitor/status.txt
temp_file=~/amscams/status.temp
export LC_NUMERIC=en_US.utf8
touch $temp_file
echo " "
echo "### station ###" > $temp_file
echo $station >> $temp_file
echo "*** station ***" >> $temp_file
echo "### date ###" >> $temp_file
date -Iseconds >> $temp_file
echo "*** date ***" >> $temp_file
echo "### who ###" >> $temp_file
who -a >>  $temp_file
echo "*** who ***" >> $temp_file
echo "### uptime ###" >> $temp_file
uptime >>  $temp_file
echo "*** uptime ***" >> $temp_file
echo "### cpu ###" >> $temp_file
echo "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND" >>  $temp_file
ps -aux | sort -nr -k 3 | head -10 >>  $temp_file
echo "*** cpu ***" >> $temp_file
echo "### sensors ###" >> $temp_file
sensors >> $temp_file
echo "*** sensors ***" >> $temp_file
echo "### mem ###" >>  $temp_file
echo "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND" >>  $temp_file
ps -aux | sort -nr -k 4 | head -10 >>  $temp_file
echo "*** mem ***" >> $temp_file
echo "### iostat ###" >>  $temp_file
iostat >>  $temp_file
echo "*** iostat ***" >> $temp_file
echo "### free ###" >>  $temp_file
free -m >>  $temp_file
echo "*** free ***" >> $temp_file
echo "### find ###" >>  $temp_file
find /mnt/ams2/HD -mmin -3 -printf '%f\t%s\n' >> $temp_file
echo "*** find ***" >> $temp_file
echo "### df ###" >>  $temp_file
df --type=ext4 >> $temp_file
echo "*** df ***" >> $temp_file
echo "### end ###" >>  $temp_file
mv $temp_file $main_file
