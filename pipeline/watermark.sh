 
# EXAMPLE WATERMARK!
# adjust input file output file

ffmpeg -i /mnt/f/meteorite_falls/2024_01_21_Germany/AMS22_2024_01_21_00_32_00_000_010031-HD-meteor-trim-0925.mp4 -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920"  /mnt/f/meteorite_falls/2024_01_21_Germany/AMS22_2024_01_21_00_32_00_000_010031-HD-meteor-trim-0925-AS7.mp4
