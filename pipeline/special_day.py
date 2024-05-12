
import datetime
"""
  
run special code to deal with events of a special day 
    
"""
import os
import glob
from lib.PipeUtil import day_or_night , load_json_file

json_conf = load_json_file("../conf/as6.json")


def backup_aurora(opt):
    # convert strings to datetime
    if os.path.exists(opt['backup_dir']) is False:
        print(f"your backup dir does not exists or you don't have permissions to write in it. {opt['backup_dir']}")
        print(f"Add or update the mount point/drive at {opt['backup_dir']} in your system.")
        return(False) 
    out_dir = opt['backup_dir'] + opt['backup_folder'] + "/"
    if os.path.exists(out_dir) is False:
        try:
            os.makedirs(out_dir)
        except:
            print(f"your backup dir does not exists or you don't have permissions to write in it. {out_dir}")
            print(f"Add or update the mount point/drive at {opt['backup_dir']} in your system.")
            return(False) 
    start_dt = datetime.datetime.strptime(opt['start_date'], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(opt['end_date'], "%Y-%m-%d %H:%M:%S")
   
    hd_files = glob.glob("/mnt/ams2/HD/*")
    
    bk_files = []
    sizes = []
    for file in sorted(hd_files):
        # get file size
        fs = os.path.getsize(file)
        
        fn = file.split("/")[-1]
        if "mp4" not in file:
            continue
        if "trim" in file:
            continue
        el = fn.split("_")
        if len(el) < 5:
            continue
        datetime_str = el[0] + "-" + el[1] + "-" + el[2] + " " + el[3] + ":" + el[4] + ":" + el[5]
        this_dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        res = day_or_night(datetime_str, json_conf)
        
        if this_dt >= start_dt and this_dt <= end_dt and res == "night":
            print(f"\rKEEP {fn} {datetime_str} {res}", end="")
            sizes.append(fs)
            bk_files.append(file)
            
    print("")
    print("Total Files To Backup:", len(bk_files))
    needed_size = sum(sizes)/ 1000000000 
    print(f"Total Size: {needed_size} GB")
    
    # check free space on the output volume/folder
    free_space_b = os.statvfs(out_dir)
    free_space = free_space_b.f_bsize * free_space_b.f_bavail / 1000000000
    print(f"Free Space: {free_space} GB")
    if free_space < needed_size * 2:
        print("Not enough space to backup the files.")
        return(False) 
    else:
        print("We have enough space to backup the requested files.")
        
        # loop over the backup files and copy them to the backup folder if they are not already there
        for file in bk_files:
            fn = file.split("/")[-1]
            cmd = f"cp {file} {out_dir}{fn}"
            if os.path.exists(out_dir + fn) is False:
                print(f"\r {cmd}", end="")
                os.system(cmd)
            else:
                print(f"\r ALREADY DID {fn}", end="")
    
   
   
opt = {}
opt['start_date'] = "2024-05-10 20:00:00"
opt['end_date'] = "2024-05-11 20:00:00"
opt['backup_dir'] = "/mnt/backup/"
opt['backup_folder'] = "2024_05_10_AURORA_BACKUP"

result = backup_aurora(opt)
if result is False:
    # backup failed try alternative directory
    opt['backup_dir'] = "/mnt/ams2/temp/"
    result = backup_aurora(opt)
        
