
#! /bin/bash
#
# Diffusion youtube avec ffmpeg

# Configurer youtube avec une résolution 720p. La vidéo n'est pas scalée.

VBR="4000k"                                    # Bitrate de la vidéo en sortie
FPS="25"                                       # FPS de la vidéo en sortie
QUAL="fast"                                  # Preset de qualité FFMPEG
#YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/cvep-ehuy-9tg5-737j"  # URL de base RTMP youtube
YOUTUBE_URL="rtmps://live-api-s.facebook.com:443/rtmp/10157538776313530?s_bl=1&s_ps=1&s_sml=0&s_sw=0&s_vt=api-s&a=AbxaYxpWnYB_oXzm"
SOURCE="rtsp://192.168.76.72/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
KEY=""                                     # Clé à récupérer sur l'event youtube

ffmpeg \
    -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero  \
    -i "$SOURCE" -deinterlace -vf scale=1280:720\
    -vcodec libx264 -pix_fmt yuv420p -preset $QUAL -r $FPS -g $(($FPS * 2)) -b:v $VBR \
    -acodec libmp3lame -ar 44100 -threads 6 -qscale 3 -b:a 712000 -bufsize 512k \
    -f flv "$YOUTUBE_URL"


