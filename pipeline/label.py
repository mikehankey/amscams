from lib.PipeUtil import load_json_file
import sys
import os
import glob

json_conf = load_json_file("../conf/as6.json")
font = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
station_id = json_conf['site']['ams_id']
date = sys.argv[1] 
hour = sys.argv[2]
minute = sys.argv[3]

meteor_dir = f"/mnt/ams2/meteors/{date}/"
wild_card_string  = f"{meteor_dir}*{date}_{hour}_{minute}*.mp4" 
outdir = "/mnt/ams2/label/"
makedirs(outdir, exists_ok=True)

files = glob.glob(wild_card_string)

for f in files:
    fn = f.split("/")[-1]
    ifile = f"{meteor_dir}{date}/{dn}"
    ofile = f"{outdir}{fn}"
    if "HD" not in file:
        continue

    cmd = f"""ffmpeg -i {ifile} -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920,drawtext=fontfile={font}:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=1060:text='{photo_credit}'" {ofile}""" 
    print(cmd)


