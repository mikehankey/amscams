sudo python3.6 -m pip install requests sklearn scikit-image
mkdir /home/ams/amscams/pipeline/models
cp /mnt/archive.allsky.tv/AMS1/ML/meteor_prev_yn.h5 /home/ams/amscams/pipeline/models
cp /mnt/archive.allsky.tv/AMS1/ML/i64.7z /home/ams/amscams/pipeline/models
cd /home/ams/amscams/pipeline/models; 7z e i64.7z
