



git pull
cp -fr /home/ams/amscams/tmp_APPS/src /mnt/archive.allsky.tv/APPS
cp -fr /home/ams/amscams/tmp_APPS/dist /mnt/archive.allsky.tv/APPS

rm /mnt/archive.allsky.tv/AMS7/REPORTS/2020/02_24/index.html
python3 /home/ams/amscams/pythonv2/doDay.py all 2020_02_24



rm /mnt/archive.allsky.tv/AMS7/REPORTS/2019/12_24/index.html
python3 /home/ams/amscams/pythonv2/doDay.py all 2019_12_24



