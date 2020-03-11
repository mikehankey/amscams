



git pull
rsync -auv /home/ams/amscams/tmp_APPS/src/* /mnt/archive.allsky.tv/APPS/src
rsync -auv /home/ams/amscams/tmp_APPS/dist/* /mnt/archive.allsky.tv/APPS/dist 
 

rm /mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/AMS7/METEOR/2019/12/24/2019_12_24_08_29_19_000_010039-trim1168.html
python3 /home/ams/amscams/pythonv2/publish.py event_station_report /AMS7/METEOR/2019/12/24/2019_12_24_08_29_19_000_010039-trim1168.json


#rm /mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.html
#python3 /home/ams/amscams/pythonv2/publish.py event_station_report /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.json



#python3 /home/ams/amscams/pythonv2/publish.py event_station_report /AMS7/METEOR/2019/12/24/2019_12_24_07_40_08_000_010041-trim0806.json




#rm /mnt/archive.allsky.tv/AMS7/REPORTS/2019/12_24/index.html
#python3 /home/ams/amscams/pythonv2/doDay.py all 2019_12_24



