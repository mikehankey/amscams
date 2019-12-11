
#! /bin/bash
#
# Diffusion youtube avec ffmpeg

# Configurer youtube avec une résolution 720p. La vidéo n'est pas scalée.

VBR="2000k"                               # Bitrate de la vidéo en sortie
FPS="20"                                  # FPS de la vidéo en sortie
QUAL="fast"                               # Preset de qualité FFMPEG
 


 # URL de base RTMP youtube
#YOUTUBE_URL="rtmps://live-api-s.facebook.com:443/rtmp/10157538776313530?s_bl=1&s_ps=1&s_sml=0&s_sw=0&s_vt=api-s&a=AbxaYxpWnYB_oXzm"
SOURCE="rtsp://192.168.76.72/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
KEY="2e88-ec97-t36t-ec68"                                     # Clé à récupérer sur l'event youtube
YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/$KEY" 
AMS_IMAGE = "/home/ams/amscam/dist/img/ams_logo_vid_anim/AMS30.png"
#-vf drawtext="text='GEMINIDES': fontcolor=white: fontsize=24: box=1: boxcolor=black@0.5:boxborderw=5: x=(w-text_w)/2: y=(h-text_h)/2" \


ffmpeg \
    -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero  \
    -i "$SOURCE" -i "$AMS_IMAGE"  \
    -filter_complex "[0]yadif[m];[m][1]overlay=25:25,realtime" -af arealtime  \
    -deinterlace \
    -vf scale=1280:720\
    -vcodec libx264 -pix_fmt yuv420p -preset $QUAL -r $FPS -g $(($FPS * 2)) -b:v $VBR \
    -acodec libmp3lame -ar 44100 -threads 6 -qscale 3 -b:a 712000 -bufsize 512k \
    -f flv "$YOUTUBE_URL"
