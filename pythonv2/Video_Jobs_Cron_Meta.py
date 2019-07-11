from Video_Jobs_Cron import video_job
from lib.UtilLib import check_running 

#TO ADD TO CRONTAB:
#python3 /home/ams/amscams/pythonv2/Video_Jobs_Cron_Meta.py > /tmp/vid.txt

#We don't do anything if the process is running 
if(check_running('Video_Jobs_Cron.py')== False):
    video_job()
else:
    print('Video_Jobs_Cron is already running for now')
