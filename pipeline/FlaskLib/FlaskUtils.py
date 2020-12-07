def get_template(file): 
   out = ""
   fp = open(file, "r")
   for line in fp:
      out += line
   fp.close()
   return(out)


def make_default_template(amsid, main_template, json_conf):
   header = get_template("FlaskTemplates/header.html")
   footer = get_template("FlaskTemplates/footer.html")
   nav = get_template("FlaskTemplates/nav.html")
   template = get_template("FlaskTemplates/" + main_template  )
   template = template.replace("{HEADER}", header)
   template = template.replace("{FOOTER}", footer)
   template = template.replace("{NAV}", nav)
   template = template.replace("{AMSID}", amsid)
   if "obs_name" in json_conf['site']:
      template = template.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   else:
      template = template.replace("{OBS_NAME}", "")
   if "location" in json_conf:
      template = template.replace("{LOCATION}", json_conf['site']['location'])
   else:
      template = template.replace("{LOCATION}", "")
   return template


def parse_jsid(jsid):
   #print("JSID:", jsid)
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

