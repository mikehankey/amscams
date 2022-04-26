import cv2
import os

def preview_rois():
   export_all_mets_dir = "/mnt/ams2/AI/DATASETS/NETWORK_PREV/ALL_METS_I64/"
   export_all_non_mets_dir = "/mnt/ams2/AI/DATASETS/NETWORK_PREV/ALL_NON_METS_I64/"
   export_all_unsure_dir = "/mnt/ams2/AI/DATASETS/NETWORK_PREV/ALL_UNSURE_I64/"
   all_dirs = [export_all_mets_dir, export_all_non_mets_dir, export_all_unsure_dir]
   for ad in all_dirs:
      if os.path.exists(ad) is False:
         os.makedirs(ad)
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
      line = line.replace("\n", "")
      if "jpg" in line:
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
         fn = img_url.split("/")[-1]
         i64_file = export_all_mets_dir + fn
         if os.path.exists(i64_file) is False:
            img = cv2.imread(line)
            img = cv2.resize(img, (64,64))
            cv2.imwrite(i64_file, img)
            print("WROTE ", i64_file)

   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/meteors.html")

   fp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.txt")
   out = ""
   for line in fp:
      if "jpg" in line:
         line = line.replace("\n", "")
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
         fn = img_url.split("/")[-1]
         i64_file = export_all_non_mets_dir + fn
         if os.path.exists(i64_file) is False:
            print("LINE", line)
            img = cv2.imread(line)
            if img is not None:
               img = cv2.resize(img, (64,64))
               cv2.imwrite(i64_file, img)
               print("WROTE ", i64_file)
            else:
               print("BAD IMG:", line)
   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/non_meteors.html")

   fp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.txt")
   out = ""
   for line in fp:
      if "jpg" in line:
         line = line.replace("\n", "")
         img_url = line.replace("/mnt/ams2", "")
         img_url = img_url.replace("\n", "")
         out += "<img src=" + img_url + ">"
         fn = img_url.split("/")[-1]
         i64_file = export_all_unsure_dir + fn
         if os.path.exists(i64_file) is False:
            img = cv2.imread(line)
            img = cv2.resize(img, (64,64))
            cv2.imwrite(i64_file, img)
            print("WROTE ", i64_file)
   ofp = open("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.html", "w")
   ofp.write(out)
   ofp.close()
   print("/mnt/ams2/AI/DATASETS/NETWORK_PREV/unsure.html")


preview_rois()
