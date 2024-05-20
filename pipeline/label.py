from lib.PipeUtil import load_json_file
import sys
import os
import glob

json_conf = load_json_file("../conf/as6.json")
font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
station_id = json_conf['site']['ams_id']
cloud_dir = f"/mnt/archive.allsky.tv/{station_id}/share/"
os.makedirs(cloud_dir, exist_ok=True)


date = sys.argv[1] 
hour = sys.argv[2]
minute = sys.argv[3]
date_string = sys.argv[4]
date_string = date_string.replace(":", "\:")
date_string = date_string.replace(",", "\,")

op_name = json_conf['site']['operator_name']
op_city = json_conf['site']['operator_city']
op_state = json_conf['site']['operator_state']
op_country = json_conf['site']['operator_country']

if "US" in op_country:
    photo_credit = f"{station_id} - {op_name} - {op_city} {op_state}, {op_country}"
else:
    photo_credit = f"{station_id} - {op_name} - {op_city}, {op_country}"

meteor_dir = f"/mnt/ams2/meteors/{date}/"
wild_card_string  = f"{meteor_dir}*{date}_{hour}_{minute}*.mp4" 
outdir = "/mnt/ams2/label/"
os.makedirs(outdir, exist_ok=True)

files = glob.glob(wild_card_string)

for f in files:
    fn = f.split("/")[-1]
    ifile = f"{meteor_dir}/{fn}"
    ofile = f"{outdir}{station_id}_{fn}"
    if "HD" not in fn:
        continue

    cmd = f"""ffmpeg -i {ifile} -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920,drawtext=fontfile={font}:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=1040:text='{photo_credit} - {date_string}'" {ofile} > /dev/null 2>&1""" 
    #cmd = f"""ffmpeg -i {ifile} -i ALLSKY7_LOGO_TRANS_640.png -filter_complex "[1:v]scale=w=320:h=140[wm];[0:v][wm]overlay=25:920,drawtext=fontfile={font}:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=5:x=25:y=1060:text='{photo_credit} '" {ofile} > /dev/null 2>&1""" 
    
    print(cmd)
    print("Please wait...")
    os.system(cmd)

    cp = f"cp {ofile} {cloud_dir}"
    print(cp)
    print("Please wait...")
    os.system(cp)
    url = f"https://archive.allsky.tv/{station_id}/share/{station_id}_{fn}"
    print("Your share URL is:")
    print(url)


