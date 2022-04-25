from lib.PipeUtil import save_json_file, load_json_file
import sys
import os

def meteor_cell(root_fn, thumb_url):
   jsid = root_fn.replace("_", "")
   datecam = ""
   click_link = "#" 
   video_url = thumb_url
   met_html = """
         <div id='{:s}' class='preview select-to norm'>
            <a class='mtt' href='{:s}' data-obj='{:s}' title='Go to Info Page'>
               <img alt='{:s}' class='img-fluid ns lz' src='{:s}'>
               <span>{:s}</span>
            </a>

            <div class='list-onl'>
               <span>{:s}<span>
            </div>
            <div class="list-onl sel-box">
               <div class="custom-control big custom-checkbox">
                  <input type="checkbox" class="custom-control-input" id='chec_{:s}' name='chec_{:s}'>
                  <label class="custom-control-label" for='chec_{:s}'></label>
               </div>
            </div>

            <div class='btn-toolbar'>
               <div class='btn-group'>
                  <a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='/dist/video_player.html?video={:s}'>
                  <i class='icon-play'></i></a>
                  <a class='delete_meteor_gallery col btn btn-danger btn-sm' title='Delete Detection' data-meteor='jsid'><i class='icon-delete'></i></a>
               </div>
            </div>
         </div>

   """.format(jsid, click_link, thumb_url, datecam, thumb_url, datecam, datecam, jsid,jsid,jsid, video_url,jsid)
   return(met_html)

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

   #out += "<div><h1>" + str(len(non_meteors)) + " non meteors found and moved.</h1><p>If you see any meteors inadvertantly placed here, you can confirm them as meteors clicking the meteor icon.</p></div><div style='clear:both'> &nbsp; </div>"


   for nmf in sorted(non_meteors, reverse=True):
      imgf = nmf.replace(".json", "-stacked-tn.jpg")
      if os.path.exists(imgf):
         img_url = imgf.replace("/mnt/ams2", "")
         cell = meteor_cell(nmf.replace(".json", ""), img_url)
         out += cell
         #out += "<img src=" + img_url + ">\n" 
   #print(out)
   out += "</div></div>" 
   fpout = open(nm_report_file, "w")
   fpout.write(out)
   fpout.close()

non_meteor_report()
