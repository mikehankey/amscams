import cv2

background = cv2.imread('/mnt/ams2/meteors/2019_08_23/2019_08_23_00_03_23_000_010040-trim-1-HD-meteor-stacked.png')
overlay = cv2.imread('./dist/img/ams_logo_vid_anim/1920x1080/AMS30.png')

added_image = cv2.addWeighted(background,0.4,overlay,0.1,0)

cv2.imwrite('/mnt/ams2/test4.png', added_image)