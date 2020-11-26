from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page
app = Flask(__name__, static_url_path='/static')



@app.route('/')
def main_menu():
   return 'Main Menu!'


@app.route('/meteors/<amsid>/<date>/<meteor_file>/')
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out

@app.route('/oldmeteors/<amsid>/<date>/<meteor_file>/')
def oldmeteor_detail_page(amsid, date, meteor_file):
   MEDIA_HOST = request.host_url.replace("5000", "80")
   METEOR_DIR = "/mnt/ams2/meteors/"
   METEOR_DIR += date + "/"
   year,mon,day = date.split("_")
   base_name = meteor_file.replace(".mp4", "")
   json_conf = load_json_file("../conf/as6.json")
   obs_name = json_conf['site']['obs_name']
   CACHE_DIR = "/mnt/ams2/CACHE/" + year + "/" + mon + "/" + base_name + "/"
   mjf = METEOR_DIR + meteor_file.replace(".mp4", ".json")
   mjrf = METEOR_DIR + meteor_file.replace(".mp4", "-reduced.json")
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
   else:
      return("meteor json not found.")

   sd_trim = meteor_file
   if "hd_trim" in mj:
      hd_trim,hdir  = fn_dir(mj['hd_trim'])
      hd_stack = hd_trim.replace(".mp4", "-stacked.jpg")
   else:
      hd_trim = None
      hd_stack = None

   sd_stack = sd_trim.replace(".mp4", "-stacked.jpg")
   half_stack = sd_stack.replace("stacked", "half-stack")
   az_grid = ""
   header = get_template("FlaskTemplates/header.html")
   header = header.replace("{OBS_NAME}", obs_name)
   header = header.replace("{AMSID}", amsid)
   footer = get_template("FlaskTemplates/footer.html")
   template = get_template("FlaskTemplates/meteor_detail.html")
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{MEDIA_HOST}", MEDIA_HOST)
   template = template.replace("{HALF_STACK}", METEOR_DIR + half_stack)
   template = template.replace("{HD_STACK}", hd_stack)
   template = template.replace("{AZ_GRID}", az_grid)
   template = template.replace("{METEOR_JSON}", mjf)
   template = template.replace("{SD_TRIM}", sd_trim)
   template = template.replace("{METEOR_REDUCED_JSON}", mjrvf)
   
   # check for reduced data
   if cfe(mjrf) == 1:
      #dt, fn, x, y, w, h, oint, ra, dec, az, el
      #frames_table = "<table border=1><tr><td></td><td>Time</td><td>Frame</td><td>X</td><td>Y</td><td>W</td><td>H</td><td>Int</td><td>Ra</td><td>Dec</td><td>Az</td><td>El</td></tr>"
      frames_table = ""
      mjr = load_json_file(mjrf)
      for mfd in mjr['meteor_frame_data']:
         dt, fn, x, y, w, h, oint, ra, dec, az, el = mfd
         date, time = dt.split(" ")
         fnid = "{:04d}".format(mfd[1])
         frame_url = MEDIA_HOST + CACHE_DIR + base_name + "-frm" + fnid + ".jpg"
         frames_table += """<tr id='fr_{:d}' data-org-x='{:d}' data-org-y='{:d}'>""".format(mfd[1], mfd[2], mfd[3])
         frames_table += """<td><div class="st" hidden style="background-color:'green'"></div></td>"""
         frames_table += """<td><img alt="Thumb #'""" + str(mfd[1]) + """'" src='""" +frame_url+ """'?c='rand' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:'green'"/></td>"""

         frames_table += """<td>{:d}</td><td>{:s} </td>""".format(int(fn), str(time)) 
         frames_table += "<td> {:0.2f} / {:0.2f}</td>".format(ra, dec)
         frames_table += "<td>{:s} / {:s}</td>".format(str(az)[0:5],str(el)[0:5])
         frames_table += """<td>{:s} / {:s}</td><td>{:s} / {:s}</td><td>{:s}</td>""".format(str(x), str(y), str(w), str(h), str(int(oint)))
         frames_table += """<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>"""
         frames_table += "</tr>"

        #table_tbody_html+= '<tr id="fr_'+frame_id+'" data-org-x="'+v[2]+'" data-org-y="'+v[3]+'">

        #<td><div class="st" hidden style="background-color:'+all_colors[i]+'"></div></td>'
        #<td><img alt="Thumb #'+frame_id+'" src='+thumb_path+'?c='+Math.random()+' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:'+all_colors[i]+'"/></td>

        #table_tbody_html+= 
        #table_tbody_html+= '<td>'+frame_id+'</td><td>'+_time[1]+'</td><td>'+v[7]+'&deg;/'+v[8]+'&deg;</td><td>'+v[9]+'&deg;/'+v[10]+'&deg;</td><td>'+ parseFloat(v[2])+'/'+parseFloat(v[3]) +'</td><td>'+ v[4]+'x'+v[5]+'</td>';
        #table_tbody_html+= '<td>'+v[6]+'</td>';

   template = template.replace("{FRAME_TABLE_ROWS}", frames_table)

   return template 
