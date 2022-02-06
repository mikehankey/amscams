import sqlite3
import random
from datetime import datetime
import numpy as np
import cv2
import json
import datetime as dt
import os
from lib.PipeUtil import load_json_file, convert_filename_to_date_cam, get_trim_num, mfd_roi, save_json_file, bound_cnt
import sys
import glob
#from Classes.ASAI import AllSkyAI
#from Classes.ASAI_Detect import ASAI_Detect

from jinja2 import Environment, PackageLoader, select_autoescape


class Dashboard():
   def __init__(self, in_data=None):
      print("ASAI DB")
      self.in_data = in_data
      self.json_conf = load_json_file("../conf/as6.json")
      self.this_station_id = self.json_conf['site']['ams_id']
      if in_data is not None:
         self.station_id = in_data['station_id']
      else:
         self.station_id = self.this_station_id
      self.cam_ids = []

      self.con1 = sqlite3.connect(self.station_id + "_ALLSKY.db")
      self.con1.row_factory = sqlite3.Row
      self.allsky_cur = self.con1.cursor()

      self.con2 = sqlite3.connect(self.station_id + "_WEATHER.db")
      self.con2.row_factory = sqlite3.Row
      self.weather_cur = self.con2.cursor()

      for cam_num in self.json_conf['cameras']:
         self.cam_ids.append(self.json_conf['cameras'][cam_num]['cams_id'])
      self.set_op_info()
      self.env = Environment(
         loader=PackageLoader("dashboard"),
         autoescape=select_autoescape()
      )

   def set_op_info(self):
      if "operator_name" in self.json_conf['site']:
         self.operator_name = self.json_conf['site']['operator_name']
      else:
         self.operator_name = None
      if "obs_name" in self.json_conf['site']:

         self.obs_name = self.json_conf['site']['obs_name']
      else:
         self.obs_name = None

      if "device_lat" in self.json_conf['site']:
         self.device_lat = self.json_conf['site']['device_lat']
      else:
         self.device_lat = None

      if "device_lng" in self.json_conf['site']:
         self.device_lat = self.json_conf['site']['device_lng']
      else:
         self.device_lng = None

      if "operator_city" in self.json_conf['site']:
         self.operator_city = self.json_conf['site']['operator_city']
      else:
         self.operator_city= None

      if "operator_state" in self.json_conf['site']:
         self.operator_state = self.json_conf['site']['operator_state']
      else:
         self.operator_state = None

      if "operator_country" in self.json_conf['site']:
         self.operator_country = self.json_conf['site']['operator_country']
      else:
         self.operator_country = None

      self.photo_credit = ""
      self.photo_credit = self.station_id + " - " + self.operator_name + " " 
      if self.operator_city is not None:
         self.photo_credit += self.operator_city 
      if self.operator_country is not None:
         if "USA" in self.operator_country or "United States" in self.operator_country or self.operator_country == "US":
            self.operator_country = "US" 
            # US Only format City, State Country
            #if self.operator_city is not None:
            #   self.photo_credit += self.operator_city
            if self.operator_state is not None:
               self.photo_credit += ", " + self.operator_state + " US"
         else:
            # International format City, Country
            if self.operator_city is not None:
               self.photo_credit += self.operator_city
            if self.operator_country is not None and self.operator_city is not None:
               self.photo_credit += ", " + self.operator_country 
            elif self.operator_country is not None: 
               self.photo_credit += self.operator_country 

      self.live_view_html = "<div>"
      self.rand = str(random.randint(1,1000))
      for cam_id in self.cam_ids:
         div_id = "latest_snap_" + cam_id
         img_url = "/latest/" + cam_id + ".jpg"
         controls = ""
         self.live_view_html += """
             <div id='""" + div_id + """' class="meteor_gallery" style="background-color: #000000; background-image: url('""" + img_url + """?""" + self.rand + """'); background-repeat: no-repeat; background-size: 192px; width: 192px; height: 108px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>

         """
      self.live_view_html += "</div>"

   def get_meteors(self, in_data):
      print("IN DATA", in_data)
      out = ""
      if in_data['req_type'] == "latest":
         sql = """
                SELECT station_id, camera_id, root_fn, start_datetime, reduced, multi_station, 
                       event_id, ang_velocity, duration, meteor_yn, ai_resp, human_confirmed
                  FROM meteors 
              ORDER BY root_fn DESC
                 LIMIT {:s}
         """.format(in_data['limit'])
      self.allsky_cur.execute(sql)
      rows = self.allsky_cur.fetchall()
      count = 1
      for row in rows:
         station_id = row[0]
         camera_id = row[1]
         root_fn = row[2]
         start_datetime = row[3]
         reduced = row[4]
         multi_station = row[5]
         event_id = row[6]
         ang_vel = row[7]
         duration = row[8]
         final_meteor_yn = row[9]
         ai_resp = row[10]
         human_confirmed = row[11]

         out += self.meteor_image(count, station_id, root_fn, final_meteor_yn, ai_resp, human_confirmed, reduced, duration, ang_vel)
         count += 1
      return(out)

   def render_widget_row(self, items):
      out = """
        <!-- START MAIN CONTENT-->
        <!-- WIDGET -->
        <div class="row">
      """
      for item in items:
         out += item
      out += """
        </div>
      """
      return(out)

   def render_widget(self, widget_id, widget_name, widget_text, widget_size, ):
      widget_start = """
        <!-- START MAIN CONTENT-->
        <!-- WIDGET -->
          <div class="col-lg-{:s}">
            <div class="card card-primary card-outline">
      """.format(str(widget_size))
      widget_end = """
            </div>
          </div>

      """
      widget_header = """
              <div class="card-header">
                <h5 class="m-0">{:s}</h5>
              </div>
      """.format(widget_name)
      widget_content = """
              <div class="card-body" style:'display: flex'>
      """
      widget_content += widget_text 
   
      rand = "123"

      widget_content += """
              </div>
      """

      widget_html = widget_start + widget_header + widget_content + widget_end
      return(widget_html)

   def render_side_nav(self, section=None, subsection=None):
      side_nav = {}
      side_nav['dashboard'] = {}
      side_nav['network'] = {}
      side_nav['events'] = {}
      side_nav['terms'] = {}
      side_nav['updates'] = {}
      side_nav['help'] = {}

      side_nav['dashboard']['name'] = "Dashboard"
      side_nav['dashboard']['sub_sections'] = ['meteors', 'weather']
      side_nav['dashboard']['sub_section_names'] = ['Meteors', 'Weather']

      side_nav['network']['name'] = "Network"
      side_nav['network']['sub_sections'] = ['local', 'region', 'world']
      side_nav['network']['sub_section_names'] = ['Local', 'Regional', 'Global']

      side_nav['events']['name'] = "Events"
      side_nav['events']['sub_sections'] = ['meteor', 'meteorites', 'space', 'weather']
      side_nav['events']['sub_section_names'] = ['Meteors', 'Meteorites', 'Space', 'Weather']

      side_nav['terms']['name'] = "Terms"
      side_nav['terms']['sub_sections'] = ['community_license', 'commercial_license', 'as7_network', 'meteorite_wg']
      side_nav['terms']['sub_section_names'] = ['Community License', 'Commercial License', 'AS7 Network Agreement', 'Meteorite Working Group Agreement']

      side_nav['updates']['name'] = "Updates" 
      side_nav['updates']['sub_sections'] = []
      side_nav['updates']['sub_section_names'] = []
      side_nav['help']['name'] = "Help"
      side_nav['help']['sub_sections'] = []
      side_nav['help']['sub_section_names'] = []


      sidebar = """
      <!-- Sidebar Menu -->
      <nav class="mt-2">
        <ul class="nav nav-pills nav-sidebar flex-column" data-widget="treeview" role="menu" data-accordion="false">
      """

      for main_item in side_nav:
         print(main_item, side_nav[main_item])
         if main_item == section:
            active_yn = "active"
         else:
            active_yn = ""
         main_name = side_nav[main_item]['name']
         if len(side_nav[main_item]['sub_sections']) > 0:
            sidebar += """
          <!-- Add icons to the links using the .nav-icon class
               with font-awesome or any other icon font library -->
          <li class="nav-item menu">
            <a href="#" class="nav-link {:s} ">
              <i class="nav-icon fas fa-tachometer-alt"></i>
              <p>
                {:s} 
                <i class="right fas fa-angle-left"></i>
              </p>
            </a>
            """.format(active_yn, main_name)
            sidebar += """
            <ul class="nav nav-treeview">
            """
            for i in range(0, len(side_nav[main_item]['sub_sections'])):
                sub_code = side_nav[main_item]['sub_sections'][i]
                sub_name = side_nav[main_item]['sub_section_names'][i]
                sidebar += """
              <li class="nav-item">
                <a href="#" class="nav-link">
                  <i class="far fa-circle nav-icon"></i>
                  <p>{:s}</p>
                </a>
              </li>

                """.format(sub_name)

            sidebar += """
            </ul>
            """
         else:
            # no subnav items
            sidebar += """
          <li class="nav-item">
            <a href="#" class="nav-link">
              <i class="nav-icon fas fa-th"></i>
              <p>
                {:s} 
              </p>
            </a>
          </li>

            """.format(main_name)
      sidebar += """
          </li>
        </ul>
      </nav>
      <!-- /.sidebar-menu -->
      """
      return(sidebar)

   def controller(self,in_data=None):
      
      template = self.env.get_template("main.html")
      if "date" in in_data:
         in_date = in_data['date']
      else:
         in_date = datetime.now().strftime("%Y-%m-%d")
         in_date_m = in_date.replace("-", "_")
 
      date_select = "<input id=tl_date name=tl_date type=date value=" + in_date + ">" 
      cam_select = "<select name=tl_cam id=tl_cam>"
      cnum = 1
      for cam_id in self.cam_ids:
         cam_select += "<option value=" + str(cnum) + ">Cam " + str(cnum) + "</option>"
         cnum += 1
      cam_select += "</select>"

      tl_iframe = """
               <iframe scrolling="no" onload="resizeIframe()" id="weather_tl" frameborder=0 src='/TL/""" + self.station_id + "/" + in_date_m + """/1/' width=100% height=360></iframe>
               <br>{:s} {:s}
      """.format(cam_select, date_select)

      tl_widget = self.render_widget("tl", "Time Lapse", tl_iframe, 6)


      weather_data, weather_text = self.get_current_weather()

      stack_text = self.recent_stacks_widget()
      stack_widget = self.render_widget("stacks", "Stacks", stack_text, 12)

      stack_widget = self.render_widget_row([stack_widget])

      weather_widget = self.render_widget("weather", "Weather", weather_text, 6)

      tl_widget = self.render_widget_row([tl_widget,weather_widget])
      
      latest_snaps_widget = self.render_widget("latest_snaps", "Current Snapshots", self.live_view_html, 12)
      latest_snaps_widget = self.render_widget_row([latest_snaps_widget])

      in_data = {}
      in_data['req_type'] = 'latest'
      in_data['limit'] = "8" 

      latest_meteors = self.get_meteors(in_data)
      latest_meteors += """
         <div style='clear:both'></div>
         <h6 class="card-title"><a href=#>More</a></h6>
      """
      latest_meteors_widget = self.render_widget("latest_meteors", "Latest Meteor Detections", latest_meteors, 12)
      latest_meteors_widget = self.render_widget_row([latest_meteors_widget])
      

   
      station_stats_text = self.station_stats()

      station_stats_widget = self.render_widget("station_stats", "Station Stats", station_stats_text, 6)
      station_stats_widget = self.render_widget_row([station_stats_widget])


      out = template.render(station_id=self.station_id, sidebar=self.render_side_nav(), latest_snaps_widget=latest_snaps_widget, latest_meteors_widget=latest_meteors_widget , tl_widget=tl_widget, stack_widget=stack_widget, station_stats_widget=station_stats_widget )
      return(out)

   def get_template(self,filename):
      temp = ""
      fp = open(filename)
      for line in fp:
         temp += line 
      return(temp)    

   
   def meteor_image(self,count, station_id, root_fn, final_meteor_yn, ai_resp, human_confirmed, reduced, duration, ang_vel):
      meteor_dir = "/mnt/ams2/meteors/" + root_fn[0:10] + "/"
      stack_file = meteor_dir + root_fn + "-stacked-tn.jpg"
      if os.path.exists(stack_file) is False:
         return("")
      meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + root_fn[0:10] + "/"
      roi_file = meteor_scan_dir + station_id + "_" + root_fn + "-ROI.jpg"
      roi_html = " NO ROI FILE? " + roi_file
      if os.path.exists(roi_file) is True:
         roi_img_url = roi_file.replace("/mnt/ams2", "") + "?" + self.rand
         roi_img_width="180"
         roi_img_height="180"
         roi_html = """<img width=120 height=120 style="border: 2px solid #ffffff" src=""" + roi_img_url + """>"""
      else:
         roi_html = "ROI FILE NOT FOUND!" + roi_file
      if True:
         stack_url = stack_file.replace("/mnt/ams2", "")
         img_width="320"
         img_height="180"
   
      main_class = ""
      if human_confirmed == 1:
         selected = "meteor"
      elif human_confirmed == -1:
         selected = "trash"
      else:
         selected = None
   
   
      buttons = self.make_trash_icon(root_fn,"#ffffff","20",selected)
   
      date_str = root_fn[0:19]
      ai_text = ""
   
      if reduced == 1:
         border_color = "gold"
      else:
         border_color = "yellow"
   
      if final_meteor_yn == 0 :
         border_color = "red"
      if human_confirmed == 1 and reduced == 1:
         border_color = "green"

      if human_confirmed == -1 :
         border_color = "red"
   
   
      if ai_resp is not None and ai_resp != "":
         ai_resp = json.loads(ai_resp)
         print("AI RESP:", ai_resp)
         if ai_resp["meteor_yn"] is True:
            ai_text += "Meteor : " + str(ai_resp['meteor_yn_confidence'])[0:4] + "<br>"
         if ai_resp["meteor_yn"] is False:
            ai_text += "Non Meteor : " + str(ai_resp['meteor_yn_confidence'])[0:4] + "<br>"
         if ai_resp["meteor_fireball_yn"] is True:
            ai_text += "Fireball : " + str(ai_resp['meteor_fireball_yn_confidence'])[0:4] + "<br>"
         ai_text += "MC: " + ai_resp['mc_class'] + " " + str(ai_resp['mc_confidence'])[0:4] + "<br>"
      else:
         ai_text = ""
      ai_text += "Dur: " + str(duration)[0:4] + "<br>"
      ai_text += "Ang Vel: " + str(ang_vel)[0:4] + "<br>"
   
      roi_div = "<div><div style='float: left'>" + roi_html + "</div><div style='float:left'>" + ai_text + "</div></div><div style='clear: both'></div>"
      html = """
         <div style='float: left'>
         <div id="{:s}" style="
           background-image: url('{:s}');
           background-repeat: no-repeat;
           background-size: {:s}px;
           width: {:s}px; height: {:s}px;
           border: 3px {:s} solid; 
           margin:5px ">
           <div class="show_hider">
   
              {:s} {:s} {:s} <br>
              {:s}
           </div>
         </div>
         <div id="{:s}_caption">&nbsp;</div>
         </div>
      """.format(root_fn, stack_url, img_width, img_width, img_height, border_color, buttons, date_str, str(count), roi_div, root_fn)
      return(html)
   
   def make_trash_icon(self,roi_file,ocolor,size,selected=None) :
      color = ocolor
      items = ['meteor', 'trash']
      trash_icons = ""
      for item in items:
         if selected == item:
            if item == 'meteor':
               color = 'lime'
            else:
               color = 'red'
         else:
            color = ocolor
         trash_icons += """
           <a href="javascript:click_icon('reclass_""" + item + """', '""" + roi_file.replace(".jpg", "") + """')">
               <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;"
                  class='fas fa-""" + item + """' title='confirm '""" + item + """' id='reclass_""" + item + """_""" + roi_file.replace(".jpg", "") + """'></i></a>

         """
      color = ocolor
      trash_icons += """
           <a href="javascript:click_icon('expand', '""" + roi_file.replace(".jpg", "") + """')">
               <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;"
                  class="bi bi-arrows-fullscreen" title="expand" id='expand_""" + roi_file.replace(".jpg", "") + """'></i></a>
           <a href="javascript:click_icon('play', '""" + roi_file.replace(".jpg", "") + """')">
               <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;"
                  class="fas fa-play-circle" title="expand" id='play_""" + roi_file.replace(".jpg", "") + """'></i></a>
      """

      trash_icons_test = """
           <a href="javascript:click_icon('reclass_trash', '""" + roi_file.replace(".jpg", "") + """')">
               <i style="padding: 5px; color: """ + color + """; font-size: """ + size + """px;"
                  class="bi bi-trash" title="non-meteor" id='reclass_trash_""" + roi_file.replace(".jpg", "") + """'></i></a>

           <a class="show_hider" href="javascript:click_icon('reclass_meteor', '""" + roi_file.replace(".jpg", "") + """')">
               <i
                  class="fas fa-meteor " title="confirm meteor" id='reclass_meteor_""" + roi_file.replace(".jpg", "") + """'></i></a>

           <a href="javascript:click_icon('reclass_trash', '""" + roi_file.replace(".jpg", "") + """')">
               <i class="bi bi-trash" title="non-meteor" id='reclass_trash_""" + roi_file.replace(".jpg", "") + """'></i></a>
           <a href="javascript:click_icon('expand', '""" + roi_file.replace(".jpg", "") + """')">
               <i class="bi bi-arrows-fullscreen" title="expand" id='expand_""" + roi_file.replace(".jpg", "") + """'></i></a>
      """




      return(trash_icons)

   def get_current_weather(self):
      sql = """
          SELECT station_id, local_datetime_key, utc_time_offset,sun_status, sun_az, sun_el, 
                 moon_status, moon_az, moon_el, forecast, actual, ai_final, samples_done 
            FROM weather_conditions
        ORDER BY local_datetime_key DESC
           LIMIT 1
      """ 
      self.weather_cur.execute(sql)
      rows = self.weather_cur.fetchall()
      station_id, local_datetime_key, utc_time_offset,sun_status, sun_az, sun_el, moon_status, moon_az, moon_el, forecast, actual, ai_final, samples_done = rows[0]

      sql = """
          SELECT observation_time, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, 
                 sea_level_pressure_mb, sky_conditions 
            FROM metar 
        ORDER BY observation_time desc limit 1
      """

      self.weather_cur.execute(sql)
      rows = self.weather_cur.fetchall()
      observation_time, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, sea_level_pressure_mb, sky_conditions = rows[0] 

      weather_data = {}
      weather_data['station_id'] = station_id
      weather_data['local_datetime_key'] = local_datetime_key 
      weather_data['utc_time_offset'] = utc_time_offset 
      weather_data['sun_status'] = sun_status
      weather_data['sun_az'] = sun_az
      weather_data['sun_el'] = sun_el
      weather_data['moon_status'] = moon_status
      weather_data['moon_az'] = moon_az
      weather_data['moon_el'] = moon_el
      weather_data['forecast1'] = forecast
      weather_data['actual'] = actual
      weather_data['ai_final'] = ai_final
      weather_data['samples_done'] = samples_done
      weather_data['observation_time'] = observation_time 
      weather_data['temp_c'] = temp_c
      weather_data['dewpoint_c'] = dewpoint_c
      weather_data['wind_dir_degrees'] = wind_dir_degrees
      weather_data['wind_speed_kt'] = wind_speed_kt
      weather_data['wind_gust_kt'] = wind_gust_kt
      weather_data['sea_level_pressure_mb'] = sea_level_pressure_mb
      weather_data['sky_conditions'] = sky_conditions


      weather_text = """
          <div class="box">
           <div class="box-body">
              <table class="table table-bordered">
                <tr>
                  <td>Local Time</td>
                  <td>{:s}</td>
                </tr>
                <tr>
                  <td>Condition</td>
                  <td>{:s}</td>
                </tr>
                <tr>
                  <td>Time of Day</td>
                  <td>{:s}</td>
                </tr>
                <tr>
                  <td>Moon</td>
                  <td>{:s}</td>
                </tr>
                <tr>
                  <td>Temp</td>
                  <td>{:s} c</td>
                </tr>
                <tr>
                  <td>Dewpoint</td>
                  <td>{:s} c</td>
                </tr>
                <tr>
                  <td>Wind Dir/Speed</td>
                  <td>{:s} / {:s} kt </td>
                </tr>
                <tr>
                  <td>Pressure</td>
                  <td>{:s}</td>
                </tr>
              </table>
            </div>
          </div>
      """.format(str(local_datetime_key), str(sky_conditions), sun_status, moon_status, str(temp_c), str(dewpoint_c), str(wind_dir_degrees), str(wind_speed_kt), str(sea_level_pressure_mb))

      return(weather_data, weather_text)

   def station_stats (self):
      sql = """
                SELECT station_id, total_meteor_obs, total_fireball_obs, total_meteors_human_confirmed, first_day_scanned,
                       last_day_scanned, total_days_scanned, ai_meteor_yes, ai_meteor_no, ai_meteor_not_scanned, ai_meteor_learning_samples,
                       ai_non_meteor_learning_samples, total_red_meteors, total_not_red_meteors, total_multi_station, 
                       total_multi_station_failed, total_multi_station_success
                  FROM station_stats
         """

      fields = ["station_id", "total_meteor_obs", "total_fireball_obs", "total_meteors_human_confirmed", "first_day_scanned", "last_day_scanned", "total_days_scanned", "ai_meteor_yes", "ai_meteor_no", "ai_meteor_not_scanned", "ai_meteor_learning_samples", "ai_non_meteor_learning_samples", "total_red_meteors", "total_not_red_meteors", "total_multi_station", "total_multi_station_failed", "total_multi_station_success"]
      self.allsky_cur.execute(sql)
      rows = self.allsky_cur.fetchall()
      stats_txt = """
          <div class="box">
           <div class="box-body">
              <table class="table table-bordered">
      """
      for i in range(0, len(rows[0])):
         field = fields[i]
         value = str(rows[0][i]) 
         stats_txt += """
                <tr>
                  <td>{:s}</td>
                  <td>{:s}</td>
                </tr>
         """.format(field, value)
      stats_txt += "</table></div></div>"
      return(stats_txt)

   def recent_stacks_widget(self):
      out = ""
      stack_dir = "/mnt/ams2/meteor_archive/" + self.station_id + "/STACKS/" 
      stack_hist = load_json_file(stack_dir + "stack_hist.json")
      out += ""
      sdata = {}
      for dir in sorted(stack_hist,reverse=True)[0:24]:
         el = dir.split("/")
         sdate = el[-2]
         if sdate not in sdata:
            sdata[sdate] = []
         sfile = el[-1]
         sdata[sdate].append (sfile)
      c = 0
      for sdate in sorted(sdata.keys(),reverse=True)[0:3]:
         c += 1       
         out += """<h5 class="m-0">""" + sdate + "</h5>"
         out += "<div>"
         for stack in sorted(sdata[sdate]):
            img_url = stack_dir.replace("/mnt/ams2", "") + sdate + "/" + stack
            controls = ""
            div_id = "ns_" + sdate + "_" + str(c)
            out += """ <div id='""" + div_id + """' class="meteor_gallery" style="background-color: #000000; background-image: url('""" + img_url + """?""" + self.rand + """'); background-repeat: no-repeat; background-size: 192px; width: 192px; height: 108px; border: 1px #000000 solid; float: left; color: #fcfcfc; margin:5px "> """ + controls + """ </div>
            """
         out += "</div><div style='clear:both'></div>"
         

      out += """<h6 class="card-title"><a href=#>More</a></h6>"""
      return(out)

   def make_options(self,opt_data, selected_val):
      options = ""
      for val, label in opt_data:
         if val == selected_val:
            options += "<option value='" + val + "' selected>" + label + "</option>"
         else:
            options += "<option value='" + val + "'>" + label + "</option>"
      return(options)
