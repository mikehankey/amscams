# First ID drive with
# sudo blkid

# Once the 1TB drive has been identified reformat it with linux ext4 file system
# sudo mkfs -t ext4 /dev/sda1

# mount the drive, chown and make the default dirs 
# sudo mount /dev/sda1 /mnt/ams2
# setup drive 1st time.sh


sudo chown -R ams:ams /mnt/ams2
mkdir /mnt/ams2/SD/
mkdir /mnt/ams2/SD/proc2
mkdir /mnt/ams2/SD/proc2/daytime
mkdir /mnt/ams2/SD/proc2/json
mkdir /mnt/ams2/HD/
mkdir /mnt/ams2/tmp
mkdir /mnt/ams2/cal
mkdir /mnt/ams2/cal/freecal
mkdir /mnt/ams2/cal/hd_images
mkdir /mnt/ams2/cal/
mkdir /mnt/ams2/cal/tmp
mkdir /mnt/ams2/trash
mkdir /mnt/ams2/latest
mkdir /mnt/ams2/CAMS
mkdir /mnt/ams2/CAMS/queue
mkdir /mnt/ams2/stations
mkdir /mnt/ams2/multi_station
mkdir /mnt/ams2/meteors
