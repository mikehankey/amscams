
import os

def preview_rois():
   cmd = "find /mnt/ams2/AI/DATASETS/NETWORK_PREV/ | grep METEOR | grep -v NON > /mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.txt "
   print(cmd)
   os.system(cmd)
   cmd = "find /mnt/ams2/AI/DATASETS/NETWORK_PREV/ | grep NON_METEOR > /mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.txt "
   print(cmd)
   os.system(cmd)
   cmd = "find /mnt/ams2/AI/DATASETS/NETWORK_PREV/ | grep UNSURE > /mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.txt "
   print(cmd)
   os.system(cmd)

   fp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.txt")
   out = ""
   for line in fp:
      if "jpg" in line:
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.html")

   fp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.txt")
   out = ""
   for line in fp:
      if "jpg" in line:
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.html")

   fp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.txt")
   out = ""
   for line in fp:
      if "jpg" in line:
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.html")


preview_rois()
