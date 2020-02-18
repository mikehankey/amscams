import sys
from lib.Video_Tools import fixmp4

# Fix an mp4
# ex:
# python3 ./pythonv2/fixmp4.py /mnt/ams2/SD/proc2/2020_02_17/2020_02_17_11_42_21_000_010039.mp4 0

mp4file = sys.argv[1] 

try:
   keep_backup = int(sys.argv[2]) 
except:
   keep_backup = 0   

fixmp4(mp4file,keep_backup)