
sudo apt-get install  --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages p7zip-full
sudo python3.6 -m pip install requests sklearn scikit-image
sudo python3.6 -m pip install redis
sudo python3.6 -m pip install boto3

mkdir /home/ams/amscams/pipeline/models
#cp /mnt/archive.allsky.tv/AMS1/ML/meteor_prev_yn.h5 /home/ams/amscams/pipeline/models
#cp /mnt/archive.allsky.tv/AMS1/ML/i64.7z /home/ams/amscams/pipeline/models
cp /mnt/archive.allsky.tv/AMS1/ML/ASAI-v2.7z /home/ams/amscams/pipeline/models
cp /mnt/archive.allsky.tv/AMS1/ML/star_yn.h5 /home/ams/amscams/pipeline/models

cd /home/ams/amscams/pipeline/models; 7z e ASAI-v2.7z


# Remove and remake the SQL ALLSKYDB
