import glob
from lib.PipeAutoCal import fn_dir

def learning_meteors_dataset():
   LEARNING_VID_DIR = "/mnt/ams2/LEARNING/METEORS/2020/VIDS/"
   files = glob.glob(LEARNING_VID_DIR + "*.mp4")
   out = ""
   for file in files:
      vfile = file.replace("/mnt/ams2", "")
      fn, dir = fn_dir(vfile)
      out += "<a href=" + vfile + ">" + fn + "</a><br>"
   return(out)
