from FlaskLib.Dashboard import Dashboard
from lib.PipeUtil import load_json_file
import math
from pprint import pprint

class LearningDash(Dashboard):
   def __init__(self):
      self.weather_repo_dir = "/mnt/ams2/datasets/weather/"
      self.weather_repo_vdir = "/datasets/weather/"
      Dashboard.__init__(self)

   def image_cell(self, img_url, ai_label, ai_label_conf,sun_status):
      img_width="180"
      img_height="180"
      div_id = img_url.split("/")[-1].replace(".jpg", "")
      border_color="black"
      buttons =""
      date_str=div_id

      in_data = {}
      in_data['label_name'] = "Current Label"
      in_data['label_options'] = []
      for tt in self.weather_labels:
         if sun_status.upper() in tt[0].upper():
            in_data['label_options'].append((tt))


      in_data['selected'] = ai_label
      button_conditions = self.button_selector(in_data)

      in_data['label_name'] = "Cloud Types"
      in_data['label_options'] = self.cloud_types
      in_data['selected'] = ""
      button_cloud_types = self.button_selector(in_data)

      in_data['label_name'] = "Precipitation"
      in_data['label_options'] = self.precip
      in_data['selected'] = ""
      button_precip = self.button_selector(in_data)

      in_data['label_name'] = "Phenomena"
      in_data['label_options'] = self.phenom
      in_data['selected'] = ""
      button_phenom = self.button_selector(in_data)




      buttons = button_conditions + button_cloud_types  + button_precip + button_phenom
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

              {:s} YO <br>
           </div>
         </div>
         <div id="{:s}_caption">&nbsp;</div>
       </div>
      """.format(div_id, img_url, img_width, img_width, img_height, border_color, buttons, date_str, div_id)
      return(html)

   def button_selector(self,in_data):
      # pass in_data as key dict with: label_name, label_options, selected 
      label_name =  in_data['label_name']
      label_options = in_data['label_options']
      selected = in_data['selected']

      options = "" 
      for lo in label_options:
         code, name = lo 
         options += """
           <a class="dropdown-item" tabindex="-1" href="#">""" + str(code) + """</a>
         """
      if selected == "":
         selected = in_data['label_name']
      out = """
      <button class="dropdown">
        <a class="dropdown-toggle" data-toggle="dropdown" href="#">
           """ + selected + """ <span class="caret"></span>
        </a>
        <div class="dropdown-menu">""" + options + """
        </div>
      </button>

      """
      return(out)

   def learning_main(self, in_data=None):
      if in_data['cmd'] == "" or in_data['cmd'] is None:
         mout = self.learning_main_menu(in_data)
         out = mout
      elif in_data['cmd'] == "weather_samples_date":
         out = self.weather_samples_date(in_data)
      elif in_data['cmd'] == "weather_samples":
         out = self.weather_samples(in_data)
      elif in_data['cmd'] == "learning_help":
         out = self.learning_help(in_data)
      else:
         out = "Command not found." + in_data['cmd']


      template = self.env.get_template("default.html")
      tout = template.render(station_id=self.station_id, sidebar=self.render_side_nav(),DEFAULT_CONTENT=out, active_learning="active")
      return(tout) 

   def learning_help(self,in_data=None):
      out = """
         <div class="card">
            <div class="card-header">
               <h3 class="card-title">ALL SKY MACHINE LEARNING README </h3>
            </div>
            <div class="card-body">
               This page is intended to explain the core machine learning concepts and functionality of the ALLSKY system. 
               <h4>Learning Concepts, Explanation and Tasks</h4>
                <ul>
                   <li>Image Features
                   <li>Data Preparation
                   <li>Labeling
                   <li>Detection
                      <ul>
                         <li>Binary (Yes/No)
                         <li>Categorical (Multi-class)
                      </ul>
                   <li>Models
                   <li>Training 
                   <li>Human Review
                   <li>Re-training
                </ul>
               <p></p>
               <h4>Weather Learning</h4>
                  <p>Weather samples are labeled or tagged in 5 dimensions:
                  <ul>
                     <li>Time of day: Day, Night, Twilight</li>
                     <li>Weather Condition: Clear, Mostly Clear, Partly Cloud, Cloudy, Overcast</li>
                     <li>Cloud Type: Cumulus, Cirrus, Stratus... </li>
                     <li>Precipitation: Raining, Snowing, Sleeting, Hail...</li>
                     <li>Phenomena: Rainbow, Sunset, Smoke, Tornado...</li>
                  </ul>
               <p></p>
               <h4>Meteor Learning</h4>
               <p></p>
               <h4>Non-Meteor Learning</h4>
               <p></p>
            </div>
         </div>
      """

      #template = self.env.get_template("default.html")
      #tout = template.render(station_id=self.station_id, sidebar=self.render_side_nav(),DEFAULT_CONTENT=out, active_learning="active")
      return(out) 

   def learning_main_menu(self, in_data=None):
      mout = ""
      options_view_types = [['']]
      options_confirm_types = [['']]
      options_time_of_day = [['']]
      options_sort_by = [['']]

      html_weather_samples = """
        
                <a class="btn btn-app">
                  <i class="fas fa-cloud"></i> Weather Samples
                </a>
         Review and relabel weather learning samples for condition, precipitation, cloud type and severe phenomena.
      """
      mout += self.render_widget("weather_samples", "<a href=?cmd=weather_samples>Weather Learning Samples</a>", html_weather_samples, 12)

      html_meteor_samples = """
                <a class="btn btn-app">
                  <i class="fas fa-meteor"></i> Meteor Samples
                </a>
         Review and relabel meteor learning samples .
      """
      mout += self.render_widget("meteor_samples", "<a href=?cmd=meteor_samples>Meteor Learning Samples</a>", html_meteor_samples, 12)

      html_non_meteor_samples = """
                <a class="btn btn-app">
                  <i class="fas fa-plane"></i> Non-Meteor Samples
                </a>
         Review and relabel non-meteor learning samples .
      """

      mout += self.render_widget("non_meteor_samples", "<a href=?cmd=non_meteor_samples>Non Meteor Learning Samples</a>", html_non_meteor_samples, 12)

      learning_help = """
                <a class="btn btn-app">
                  <i class="fas fa-question"></i> Read Me
                </a>
               
      """

      mout += self.render_widget("learning_help", "<a href=?cmd=learning_help>Help & Explaination</a>", learning_help, 12)


      return(mout)

   def learning_weather_search_form(self, in_data):
  
      # current labels 
      self.weather_labels = self.get_weather_labels(in_data)
      self.label_options = ""
      for row in self.weather_labels:
         self.label_options += "<option value='" + row[0] + "'>" + row[0] + "</option>"

      self.weather_cloud_types = load_json_file("weather_cloud_types.json")
      self.cloud_types = []

      self.weather_condition = load_json_file("weather_condition.json") 
      self.weather_phenomena = load_json_file("weather_phenomena.json") 
      self.weather_severe = load_json_file("weather_severe.json") 

      self.weather_precip = load_json_file("weather_precip.json") 
      self.precip = []
      for condition in self.weather_precip:
         self.precip.append((condition, condition))

      opt_phenom = []
      opt_phenom.append(("all", "All"))
      opt_phenom.append(("none", "None"))
      self.phenom = []
      for condition in self.weather_phenomena:
         code = condition.lower()
         opt_phenom.append((code,condition))
         self.phenom.append((code, condition))
      for condition in self.weather_severe:
         code = condition.lower()
         opt_phenom.append((code,condition))
      self.phenom_options = self.make_options(sorted(opt_phenom), "")


      # condition 

      opt_condition = []
      opt_condition.append(("All", "All"))
      for condition in self.weather_condition:
         code = condition.lower()
         opt_condition.append((code,condition))
      self.condition_options = self.make_options(sorted(opt_condition), "")

      # cloud types 
      opt_cloud_types = []
      opt_cloud_types.append(("All", "All"))
      for alt,ctypes in self.weather_cloud_types:
         for ct in ctypes:
            opt_cloud_types.append((ct,ct)) 
            self.cloud_types.append((ct,ct))
      self.cloud_type_options = self.make_options(sorted(opt_cloud_types), "")

      opt_precip = []
      opt_precip.append(("All", "All"))
      for ppp in self.weather_precip:
         code = ppp.lower()
         code = code.replace(" ", "_")
         code = code.replace("(", "")
         code = code.replace(")", "")
         opt_precip.append((code,ppp))
      self.precip_options = self.make_options(sorted(opt_precip), "")



      # confirm status
      opt_confirm = [['All', 'All'], ['human_confirmed', 'Human Confirmed'], ['not_confirmed', 'Not Human Confirmed']]
      self.confirm_options = self.make_options(sorted(opt_confirm), "")

      # time of day options
      opt_tod = [['All', 'All'], ['day', 'Day'],['Night', 'Night'], ['Twilight', 'Twilight']]
      self.tod_options = self.make_options(sorted(opt_tod), "")
 
      self.sort_options= ""

      form = """

         <div class="card">
            <div class="card-header">
               <h3 class="card-title">Search Options</h3>
            </div>
            <div class="card-body">
            <form action="/DASHBOARD/{:s}/METEORS">
            <input type='hidden' name=cmd value='metgal'>
            <div class="row">
              <div class="col-2">
                  <label for="view_type">Current Label</label>
                  <select class="custom-select rounded-0" id="view_type" name="view_type">""" + self.label_options + """
                  </select>
               </div>
               <div class="col-2">
                  <label for="red_status">Time of Day</label>
                  <select class="custom-select rounded-0" id="time_of_day" name="time_of_day">""" + self.tod_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="confirm_status">Weather Condition</label>
                  <select class="custom-select rounded-0" id="confirm_status" name="confirm_status">""" + self.condition_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="cloud_type">Cloud Type</label>
                  <select class="custom-select rounded-0" id="confirm_status" name="cloud_type">""" + self.cloud_type_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="precipitation">Precipitation</label>
                  <select class="custom-select rounded-0" id="confirm_status" name="precipitation">""" + self.precip_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="phenom">Phenomena</label>
                  <select class="custom-select rounded-0" id="phenom" name="phenom">""" + self.phenom_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="confirm_status">Confirmation Status</label>
                  <select class="custom-select rounded-0" id="confirm_status" name="confirm_status">""" + self.confirm_options + """
                  </select>
               </div>

               <div class="col-2">
                  <label for="sort_by">Sort By</label>
                <div class="input-group input-group-md">
                  <select class="custom-select rounded-0" id="sort_by" name="sort_by">""" + self.sort_options + """
                  </select>
                    <button type="submit" class="btn btn-info btn-flat">Go!</button>
                 </div>
               </div>
             </div>
           </div>
         </div>
         </form>
      """.format(self.station_id)
      return(form)

   #def get_conditions_days(self, date):
   #   sql = """ 
   #          SELECT 

   def weather_samples_date(self, in_data):
      out = "Weather Samples By Date"
      out += self.learning_weather_search_form(in_data)
      ipp = 1000
      offset = 0
      if True:
         #where = "WHERE ai_sky_condition = '{:s}' ".format(label)
         where = "WHERE ai_sky_condition like '%DAY%' "
         sql_order_by = "filename ASC"
         sql = """
                SELECT A.filename, A.local_datetime_key, A.ai_sky_condition, A.ai_sky_condition_conf ,
                       B.sun_status, B.forecast
                       
                  FROM ml_weather_samples A
            INNER JOIN weather_conditions B 
                    ON A.local_datetime_key = B.local_datetime_key 
                       {:s}
              ORDER BY {:s}
                 LIMIT {:s} OFFSET {:s}
         """.format(str(where), sql_order_by, str(ipp), str(offset))

         self.weather_cur.execute(sql)
         rows = self.weather_cur.fetchall()
         last_froot = ""
         pc = 0
         samps = []
         for row in rows:
            filename = row[0]
            froot = filename.split("-")[0]
            local_datetime_key = row[1]
            ai_sky_condition = row[2]
            ai_sky_condition_conf = row[3]
            sun_status = row[4]
            forecast = row[5]
            img_url = self.weather_repo_vdir + ai_sky_condition + "/" + filename
            if froot != last_froot:
               #out += "<br>" + froot + "<br>"
               pc = 0
               out += self.display_samples(samps)
               samps = []
            samps.append([img_url, ai_sky_condition, ai_sky_condition_conf, sun_status,forecast])

            last_froot = froot 
            pc += 1

      return(out)

   def display_samples(self, samples):
      if len(samples) == 0:
         return("")
      row1 = ""
      row2 = ""
      div_id = samples[0][0].split("/")[-1].replace(".jpg", "")
      cells = self.init_cells()
      for img_url, ai_sky_condition, ai_sky_condition_conf, sun_status, forecast in sorted(samples):
         # pass in_data as key dict with: label_name, label_options, selected



         sample = img_url.split("/")[-1]
         num = sample.split("-")[-1].replace(".jpg", "")
         cells[num] = self.image_cell(img_url, ai_sky_condition, ai_sky_condition_conf,sun_status)

      print("CELLS:", cells)
      out = """
         <div>
           {:s} {:s} {:s}
           <table>
              <tr>
                 <td>{:s}</td>
                 <td>{:s}</td>
                 <td>{:s}</td>
                 <td>{:s}</td>
              </tr>
              <tr>
                 <td>{:s}</td>
                 <td>{:s}</td>
                 <td>{:s}</td>
                 <td>{:s}</td>
              </tr>
         </div>
         <div style='clear:both'><br></div>
      """.format(div_id, sun_status, forecast, cells['0'], cells['1'], cells['2'], cells['3'], cells['4'], cells['5'], cells['6'], cells['7'])

      return(out)         

   def init_cells(self):
      cells = {}
      for i in range(0, 8):
         cells[str(i)] = ""
      return(cells)

   def weather_samples(self, in_data):
      if "label" in in_data:
         label= in_data['label']
      else:
         label = "" 
      if "ipp" in in_data:
         ipp = in_data['ipp']
      else:
         ipp = 1000
      if "offset" in in_data:
         offset = in_data['offset']
      else:
         offset = 0
      if label is not None and label != "":
         where = "WHERE ai_sky_condition = '{:s}' ".format(label)
         sql_order_by = "filename ASC"
         sql = """
                SELECT filename, local_datetime_key, ai_sky_condition, ai_sky_condition_conf 
                  FROM ml_weather_samples 
                       {:s}
              ORDER BY {:s}
                 LIMIT {:s} OFFSET {:s}
         """.format(str(where), sql_order_by, str(ipp), str(offset))
         print(sql)
         self.weather_cur.execute(sql)
         rows = self.weather_cur.fetchall()
         out = "Weather Samples<br>"
         last_froot = ""
         for row in rows:
            filename = row[0]
            froot = filename.split("-")[0]
            local_datetime_key = row[1]
            ai_sky_condition = row[2]
            ai_sky_condition_conf = row[3]
            img_url = self.weather_repo_vdir + ai_sky_condition + "/" + filename

            out += "<img src={:s} alt='{:s} {:s}'>".format(img_url, ai_sky_condition, str(ai_sky_condition_conf))
            last_froot = froot
      else:
         # label menu
         sql = """
                SELECT ai_sky_condition, count(*) 
                  FROM ml_weather_samples
              GROUP BY ai_sky_condition
              ORDER BY ai_sky_condition
         """
         print(sql)
         self.weather_cur.execute(sql)
         rows = self.weather_cur.fetchall()
         out = "<a href=?cmd=weather_samples_date>Weather Samples By Date</a><br>"
         out += "Weather Samples by Condition Label<ul>"
         for row in rows:
            label = row[0]
            count = str(int(row[1]))
            out += """
               <li><a href=?cmd=weather_samples&label={:s}>{:s} ({:s})</a></li>
            """.format(label,label,count)
         out += "</ul>"

      return(out )

   def get_weather_labels (self, in_data=None):

      sql = """
         SELECT ai_sky_condition, count(*)
           FROM ml_weather_samples
          GROUP BY ai_sky_condition
          ORDER BY ai_sky_condition
      """
      self.weather_cur.execute(sql)
      rows = self.weather_cur.fetchall()
      data = []
      data.append(("All", len(rows)))
      for row in rows:
         label = row[0]
         count = str(int(row[1]))
         data.append((label,count))
      return(data)
