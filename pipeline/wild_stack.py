import os, sys, glob

#give full path and string to wild ending with NO stars! instead use % for stars 

wild = sys.argv[1]
wild = wild.replace("%", "*")
print("WILD:", wild, "END")
files = glob.glob(wild)
print("FILES:", files)
for f in files:
   if ".mp4" not in f:
      continue
   outf = f.replace(".mp4", ".jpg")
   if os.path.exists(outf) is False:
      cmd = "python3 stack_fast.py " + f
      print(cmd)
      os.system(cmd)
   else:
      print("Already done", outf)


wel = wild.split("/")
fn = wel[-1]
wdir = wild.replace(fn, "")

jpgs = glob.glob(wdir + "*stacked*.jpg")
html = ""
for j in sorted(jpgs):
    jfn = j.split("/")[-1]
    vfn = jfn.replace("-stacked.jpg", ".mp4")
    html += "<a href={:s}><img src={:s}></a><br>{:s}<br>".format(vfn, jfn, jfn)

out = open(wdir + "stacked.html", "w")
out.write(html)
out.close()
print(wdir + "stacked.html")


