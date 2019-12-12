import sys
import os
 
from lib.FileIO import *


# Setup a live streaming on Youtube
VBR="1000k"                               
FPS="20"                              
QUAL="MEDIUM"  

 
# CAM IP
try:
   sys.argv[1]
   CAM_IP = sys.argv[1]
except:
   CAM_IP= "192.168.76.71"

# YOUTUBE Key
try:
   sys.argv[2]
   KEY = sys.argv[2]
except:
   KEY="2e88-ec97-t36t-ec68"       

# Overlay Image
try:
   sys.argv[3]
   OVERLAY = sys.argv[3]
except:
   OVERLAY="/home/ams/amscams/dist/img/1280x720/AMS_UA.png"    
   
# Text
try:
   sys.argv[4]
   TEXT = sys.argv[4]
except:
   TEXT = "GEMINIDS 2019 - Live from West Virginia"    


SOURCE="rtsp://"+CAM_IP+"/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/"+KEY

cmd = 'ffmpeg \
      -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -i "'+SOURCE+'" -i "'+OVERLAY+'" \
      -filter_complex "[1:v]scale=1280x720[scaled];\
      [scaled]drawtext=:text="'+TEXT+'":fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@0.45:fontsize=14:x=20:y=20[texted]; \
      [texted]yadif[m];[m][2]overlay=25:25" \
      -vcodec libx264 -pix_fmt yuv420p -preset '+QUAL+' -r '+FPS+' -g $(('+FPS+'  * 2)) -b:v '+VBR+'  \
      -acodec libmp3lame -ar 44100 -threads 6 -qscale 3 -b:a 712000 -bufsize 512k \
      -f flv "'+YOUTUBE_URL+'"'

os.system(cmd)