cp /mnt/ams2/SD/proc2/2018_12_05/2018_12_05_06_19_18_000_010006.mp4 /mnt/ams2/CAMS/queue/
cp /mnt/ams2/SD/proc2/rejects/2018_12_05_06_19_18_000_010006-motion.txt /mnt/ams2/CAMS/queue/
./parse-motion.py /mnt/ams2/CAMS/queue/2018_12_05_06_19_18_000_010006-motion.txt 
./reject-filters.py check_for_motion /mnt/ams2/SD/proc2/2018_12_05/2018_12_05_06_19_18_000_010006-trim1.mp4

