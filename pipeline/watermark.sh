 
# EXAMPLE WATERMARK!
# adjust input file output file

#ffmpeg -i /mnt/f/meteorite_falls/2024_01_21_Germany/AMS22_2024_01_21_00_32_00_000_010031-HD-meteor-trim-0925.mp4 -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920"  /mnt/f/meteorite_falls/2024_01_21_Germany/AMS22_2024_01_21_00_32_00_000_010031-HD-meteor-trim-0925-AS7.mp4

ffmpeg -i /mnt/f/meteorite_falls/2024_09_10_Polaris_Dawn/output/2024_09_10_09_34_00_polaris-dawn.mp4 -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920,drawtext=fontfile=/path/to/font.ttf:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=1060:text='SpaceX Polaris Dawn Mission captured on AllSky7 station AMS1 by Mike Hankey, Monkton, MD'" /mnt/f/meteorite_falls/2024_09_10_Polaris_Dawn/output/2024_09_10_09_34_00_polaris-dawn-as7.mp4
