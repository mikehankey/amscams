# purge all meteor dirs that match mask rejects
import os

mdir = "/mnt/ams2/meteors/"
dirs = os.listdir(mdir)
for d in dirs:
    if os.path.isdir(mdir + d) is True:
        day = d.split("/")[-1]
        if "20" == day[:2]:
            cmd = "./Process.py reject_masks " + day
            os.system(cmd)

            # FAST SYNC
            cmd = "python3 ./Meteor.py 10 " + day
            os.system(cmd)

            # sync up dyna deletes with local deletes
            cmd = "python3 Rec.py del_aws_day " + day
            print(cmd)
            os.system(cmd)
