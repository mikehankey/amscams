import os

# Setup a live streaming on Youtube
VBR="2500k"                               
FPS="25"                              
QUAL="medium"  


cur = "KEVIN"

#### VISHNU - AMS23 - ARIZONA  
if(cur=="VISHNU"):
   CAM_IP= "192.168.76.71" # CAM IP
   KEY="2e88-ec97-t36t-ec68" # YOUTUBE Key
   OVERLAY="/home/ams/amscams/dist/img/1280x720/AMS_UA.png" # Overlay Image
   TEXT = "Cam Operator\: Vishnu Reddy, UA" # Text

#### ELISABETH WARNER - AMS9 - MARYLAND
if(cur=="ELIZABETH"):
   CAM_IP="192.168.76.73"
   KEY="3b5j-sy7c-fc12-57za" # YOUTUBE Key
   OVERLAY="/home/ams/amscams/dist/img/1280x720/AMS_UMD.png" # Overlay Image
   TEXT = "Cam Operator\: Elizabeth Warner, UMD" # Text

#### BOB LUNDSFORD - AMS24 - CA
if(cur=="BOB"):
   CAM_IP="192.168.76.72"
   KEY="4jv8-z9u9-ywqb-0sgu" # YOUTUBE Key
   OVERLAY="/home/ams/amscams/dist/img/1280x720/AMS.png" # Overlay Image
   TEXT = "Cam Operator\: Bob Lundsford, CA" # Text

#### Kevin Palivec  - AMS24 - TX
if(cur=="KEVIN"):
   CAM_IP="192.168.76.72"
   KEY="rfs0-67vm-dtwj-6k64" # YOUTUBE Key
   OVERLAY="/home/ams/amscams/dist/img/1280x720/AMS.png" # Overlay Image
   TEXT = "Cam Operator\: Kevin Palivec, TX" # Text
 
SOURCE="rtsp://"+CAM_IP+"/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/"+KEY


cmd = 'ffmpeg \
      -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -i "'+SOURCE+'" -i "'+OVERLAY+'" \
      -filter_complex "[1:v]scale=1280x720[scaled];\
      [scaled]drawtext=:text=\'' + TEXT +'\':fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@0.45:fontsize=14:x=20:y=20[texted]; \
      [texted]yadif[m];[m][2]overlay=25:25[out]" \
      -vcodec libx264 -pix_fmt yuv420p -preset '+QUAL+' -r '+FPS+' -g $(('+FPS+' * 2)) -b:v '+VBR+' \
      -ac 1 -crf:v 3 -b:a 712000 -bufsize 128k -maxrate ' + VBR +' -map "[out]" -map 0:a -c:a copy \
      -f flv "'+YOUTUBE_URL+'"'
 
#print(cmd)

for x in range(30):
   os.system(cmd)