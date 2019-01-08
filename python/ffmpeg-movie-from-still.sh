#/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '/mnt/ams2/HD/tmp3/sync/6/*.png' \
#  -c:v libx264 -r 25 -pix_fmt yuv420p /mnt/ams2/out6.mp4
/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '/mnt/ams2/HD/tmp3/sync/all/*.png' \
  -c:v libx264 -r 25 -pix_fmt yuv420p /mnt/ams2/2019-HD-quads.mp4
