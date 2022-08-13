import os, sys, glob

#give full path and string to wild ending with star
wild = sys.argv[1]
files = glob.glob(wild)
for f in files:
   outf = f.replace(".mp4", ".jpg")
   if os.path.exists(outf) is False:
      cmd = "python3 stack_fast.py " + f
      print(cmd)
      os.system(cmd)

wel = wild.split("/")
fn = wel[-1]
wdir = wild.replace(fn, "")

jpgs = glob.glob(wdir + "*stacked*.jpg")
html = ""
for j in jpgs:
    jfn = j.split("/")[-1]
    print("JPG:", jfn)
    html += "<img src={:s}><br>{:s}<br>".format(jfn, jfn)

out = open(wdir + "stacked.html", "w")
out.write(html)
out.close()
print(wdir + "stacked.html")


