import glob
import argparse
import os
import sys
from lib.PipeUtil import load_json_file

class MeteorReducer:
    # This class should handle QA & reductions for Meteor Observation
    # methods should include :
    #   -- validating / importing
    #   -- re-reducing
    #   -- calibrating
    #
    def __init__(self, obs_id=None, obs_day=None):
        # basic data fields
        self.obs_id = obs_id 
        self.obs_day = obs_day
        self.json_conf = load_json_file("../conf/as6.json")
        self.station_id = self.json_conf['site']['ams_id']
        self.mdir = "/mnt/ams2/meteors"
        self.archive_dir = "/mnt/archive.allsky.tv/" + self.station_id

    def load_json_file(self, json_file):
        if True:
            with open(json_file, 'r' ) as infile:
                json_data = json.load(infile)
        return json_data

    def save_json_file(self, json_file, json_data, compress=False):
        if "cp" in json_data:
            if json_data['cp'] is not None:
                for key in json_data['cp']:
                    if type(json_data['cp'][key]) == np.ndarray:
                        json_data['cp'][key] = json_data['cp'][key].tolist()
        if "calparams" in json_file or "multi" in json_file:
            for key in json_data:
                if type(json_data[key]) == np.ndarray:
                    json_data[key] = json_data[key].tolist()

        with open(json_file, 'w') as outfile:
            if(compress==False):
                json.dump(json_data, outfile, indent=4, allow_nan=True )
            else:
                json.dump(json_data, outfile, allow_nan=True)
        outfile.close()

    def meteor_filename(self,  meteor_id):
        if ".mp4" in meteor_id:
            meteor_id = meteor_id.replace(".mp4", "")
        if ".json" in meteor_id:
            meteor_id = meteor_id.replace(".json", "")
        if "AMS" in meteor_id:
            station_id = meteor_id.split("_")[0]
            meteor_id = meteor_id.replace(station_id + "_", "")
        date = meteor_id[0:10]
        mfile = self.mdir + "/" + date + "/" + meteor_id + ".json"
        return(mfile)

    def get_meteor_files_for_day(self,  obs_day):
        meteor_dir = self.mdir + "/" + obs_day + "/" 
        files = glob.glob(meteor_dir + "*.json")
        mfiles = []
        rfiles = []
        for f in files:
            if "frame" not in f and "events" not in f and "index" not in f and "cloud" not in f and "import" not in f and "report" not in f and "reduced" not in f and "calparams" not in f and "manual" not in f and "starmerge" not in f and "master" not in f:
                mfiles.append(f)
            elif "reduced" in f:
                rfiles.append(f)
        return(mfiles, rfiles)

    def get_meteor_days(self ):
        mdayx = os.listdir(self.mdir)
        mdays = []
        for md in sorted(mdayx):
            if os.path.isdir(self.mdir + "/" + md) is True and md[0:2] == "20":
                mdays.append(md)
        return(mdays)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Utility to reduce or re-reduce existing meteors in the /mnt/ams2/meteors/ directory")

    # Define the command-line arguments

    # Additional arguments can be added similarly
    parser.add_argument("--cmd", choices=["reduce_meteor", "reduce_day", "reduce_check_all"], help="Command you want to run.")
    parser.add_argument("--date", type=str, help="Day to run for batch")
    parser.add_argument("--meteor", type=str, help="Meteor MP4 or JSON file")
    parser.add_argument("--force", type=bool, help="If a meteor has already been reduced, this must be True to re-run")
    args = parser.parse_args()


    #print(args.cmd)
    #print(args.date)
    #print(args.meteor)
    if args.cmd == "reduce_check_all":
        MR = MeteorReducer()
        mdays = MR.get_meteor_days()
        for day in sorted(mdays, reverse=True): 
            print("DAY:", day)
            mfiles, rfiles = MR.get_meteor_files_for_day(obs_day=day)
            for mfile in mfiles:
                rfile = mfile.replace(".json", "-reduced.json")
                mfn = mfile.split("/")[-1].replace(".json", ".mp4")
                if os.path.exists(rfile) is False:
                    try:
                        jdata = load_json_file(mfile)
                    except:
                        print("error loading:", mfile)
                        continue
                    if "fireball_fail" not in jdata:
                        cmd = "./Process.py fireball " + mfn
                        print(cmd)
                        os.system(cmd)
                        print(cmd)
                    else:
                        print("Skip we have tried and failed already.", jdata['fireball_fail'])
    if args.cmd == "reduce_day":
        MR = MeteorReducer(obs_day=args.date)
        mfiles, rfiles = MR.get_meteor_files_for_day(obs_day=args.date)
        print("Meteor Detected/Reduced:", len(mfiles), len(rfiles))
        for mfile in mfiles:
            rfile = mfile.replace(".json", "-reduced.json")
            mfn = mfile.split("/")[-1].replace(".json", ".mp4")
            if os.path.exists(rfile) is False:
                cmd = "./Process.py fireball " + mfn
                print(cmd)
                os.system(cmd)


    if args.cmd == "reduce_meteor":
        MR = MeteorReducer(obs_id=args.meteor)
        mfile = MR.meteor_filename(args.meteor)
        red_file = mfile.replace(".json", "-reduced.json")
        cmd = "./Process.py fireball " + args.meteor
        print(cmd)
        os.system(cmd)
