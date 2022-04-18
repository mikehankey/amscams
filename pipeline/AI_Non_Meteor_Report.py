from lib.PipeUtil import save_json_file, load_json_file
import sys
import os

def non_meteor_report():
   # update the non-meteor report for ALL days:
   non_meteors = []   
   nm_data_file = "/mnt/ams2/non_meteors/non_meteors.txt"
   nm_json_file = "/mnt/ams2/non_meteors/non_meteors.json"
   nm_report_file = "/mnt/ams2/non_meteors/non_meteors.html"
   cmd = "find /mnt/ams2/non_meteors/ |grep json |grep -v redu > " + nm_data_file
   os.system(cmd)
   out = ""

   
   fp = open("header.html")
   for line in fp:
      out += line

   fp = open(nm_data_file)
   for line in fp:
      line = line.replace("\n", "")
      non_meteors.append(line)

   out += "<h1>" + str(len(non_meteors)) + " non meteors found and moved.</h1>"
   out += "<p>If you see any meteors inadvertantly placed here, you can confirm them as meteors clicking the meteor icon.</p>"


   for nmf in sorted(non_meteors, reverse=True):
      imgf = nmf.replace(".json", "-stacked-tn.jpg")
      if os.path.exists(imgf):
         img_url = imgf.replace("/mnt/ams2", "")

         out += "<img src=" + img_url + ">\n" 
   print(out)
   fpout = open(nm_report_file, "w")
   fpout.write(out)
   fpout.close()

non_meteor_report()
