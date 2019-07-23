import os
import time
from lib.VIDEO_VARS import * 

AFTER_DAYS = 7;

current_time = time.time() 

for f in os.listdir(VID_FOLDER):
    creation_time = os.path.getctime(f)
    if (current_time - creation_time) // (24 * 3600) >= 7:
        os.unlink(f)
        print('{} removed'.format(f))


if (current_time - creation_time) // (24 * 3600) >= 7:
    #os.unlink(f)
    print('{} removed'.format(f))