import os, sys, glob

#give full path and string to wild ending with star
wild = sys.argv[1]
files = glob.glob(wild)
for f in files:
   cmd = "python3 stack_fast.py " + f
   print(cmd)
   os.system(cmd)
   exit()

