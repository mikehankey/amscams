import time
from datetime import datetime as dt

def get_version(json_conf):
   if "git_revision" in json_conf:
       version_info = "v" + str(json_conf['git_revision'])
   else:
      version_info = "UNKNOWN ASOS VERSION PLEASE RUN ./gitpull.py in the amscams/pipeline dir AND THEN REBOOT SERVER"
   if "git_last_update" in json_conf:
      version_info += " Last updated on " + json_conf['git_last_update']
   copywrite_info = "&copy; Copyright Mike Hankey LLC "  + str(dt.now().strftime("%Y"))
   return(version_info, copywrite_info)

def get_template(file): 
   out = ""
   fp = open(file, "r")
   for line in fp:
      out += line
   fp.close()
   return(out)

def network_nav(json_conf): 
   net_nav = """
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="/NETWORK/" id="network" data-toggle="dropdown">Network</a>
            <div class="dropdown-menu dropdown-menu-right">
              <a class="dropdown-item" href="/NETWORK/MAP/{AMSID}/">Network Map</a>
              <a class="dropdown-item" href="/NETWORK/METEORS/{AMSID}/">Meteor Events</a>
            </div>
        </li>
            <!--
        <li class="nav-item"><a class="nav-link" href="/NETWORK/{AMSID}">NETWORK</a></li>
            -->
   """
   return(net_nav)

def make_default_template(amsid, main_template, json_conf):
   remote = 1
   version_info, copywrite_info = get_version(json_conf)
   if remote == 1:
      header = get_template("FlaskTemplates/header-remote.html")
      footer = get_template("FlaskTemplates/footer-remote.html")
      footer = footer.replace("{VERSION_INFO}", version_info)
      footer = footer.replace("{COPYWRITE}", copywrite_info)
      print("YO")
   else:
      header = get_template("FlaskTemplates/header.html")
      footer = get_template("FlaskTemplates/footer.html")
      print("YO2")

   nav = get_template("FlaskTemplates/nav.html")

   if "my_network" in json_conf:
      net_nav = network_nav(json_conf)
      nav = nav.replace("<!--NETWORK-->", net_nav)
   else:
      print("NO NETWORK!")


   template = get_template("FlaskTemplates/" + main_template  )
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{AMSID}", amsid)
   ts = time.time()
   if "obs_name" in json_conf['site']:
      template = template.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   else:
      template = template.replace("{OBS_NAME}", "")
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")
   template = template.replace("{RAND}", str(time.time())[0:10])
   return template


def parse_jsid(jsid):
   year = jsid[0:4]
   month = jsid[4:6]
   day = jsid[6:8]
   hour = jsid[8:10]
   min = jsid[10:12]
   sec = jsid[12:14]
   micro_sec = jsid[14:17]
   cam = jsid[17:23]
   trim = jsid[24:]
   trim = trim.replace(".json", "")
   video_file = "/mnt/ams2/meteors/" + str(year) + "_" + str(month) + "_" + str(day) + "/"  + year + "_" + month + "_" + day + "_" + hour + "_" + min + "_" + sec + "_" + micro_sec + "_" + str(cam) + "-" + trim + ".mp4"
   return(video_file)

