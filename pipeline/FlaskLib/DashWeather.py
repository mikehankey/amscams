from FlaskLib.Dashboard import Dashboard
import simplejson as json
import datetime
import math
from pprint import pprint

class WeatherDash(Dashboard):
   def __init__(self):

      Dashboard.__init__(self)


   def weather_main_menu(self, in_data=None):

      html_network_live_view = """
         Most recent snapshots from stations in your region.  
      """
      mout = self.render_widget("snap_archive", "<a href=?cmd=network_live_view>Network Live View</a>", html_network_live_view, 12)

      html_snap_archive = """
         View 15-minute snapshot history. 
      """
      mout += self.render_widget("snap_archive", "<a href=?cmd=snap_archive>Snapshot Archive</a>", html_snap_archive, 12)

      html_metar_log = """
         Browse metar record log. 
      """
      mout += self.render_widget("metar_log", "<a href=?cmd=metar_log>Metar Log</a>", html_metar_log, 12)

      html_weather_conditions_log = """
         Browse AS7 weather conditions log. 
      """
      mout += self.render_widget("weather_conditions_log", "<a href=?cmd=weather_conditions_log>Weather Conditions Log</a>", html_weather_conditions_log, 12)

      html_weather_samples = """
         Review and relabel AS7 weather samples . 
      """
      mout += self.render_widget("weather_samples", "<a href=?cmd=weather_samples>Weather Learning Samples</a>", html_weather_samples, 12)

      html_weather_config = """
         Review and edit weather configuration and API account services. 
      """
      mout += self.render_widget("weather_config", "<a href=?cmd=weather_config>Weather Config</a>", html_weather_config, 12)




      return(mout)
  
   def get_metar(self, date_str):
      sql = """
         SELECT station_id, observation_time, latitude, longitude, elevation_m, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, visibility_statute_mi, sea_level_pressure_mb, sky_conditions
           FROM metar
          WHERE observation_time like ?
      """
      svals = ["%" + date_str + "%"]
      self.weather_cur.execute(sql,svals)
      rows = self.weather_cur.fetchall()
      return(rows) 

   def get_samples_results(self, date_str):
      sql = """
         SELECT local_datetime_key, ai_sky_condition, ai_sky_condition_conf
           FROM ml_weather_samples 
          WHERE local_datetime_key like ?
      """
      svals = ["%" + date_str + "%"]
      self.weather_cur.execute(sql,svals)
      rows = self.weather_cur.fetchall()
      return(rows) 

 
   def snap_archive(self, in_data=None):
      html_snap_archive = """
         Snap Archive...
      """
      ipp = 500
      offset = 0
      if "date" not in in_data:
         date = datetime.datetime.now().strftime("%Y_%m_%d")
      else:
         date = in_data['date']

      metars = self.get_metar(date)
      metar_dict = {}
      metar_html = ""
      for row in metars:
         (station_id, observation_time, latitude, longitude, elevation_m, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, visibility_statute_mi, sea_level_pressure_mb, sky_conditions) = row
         obs_time = observation_time.replace("Z", "")
         obs_time = obs_time.replace("T", "_")
         obs_time = obs_time.replace("-", "_")
         obs_time = obs_time.replace(":", "_")
         print("OBS TIME:", obs_time)
         year, month, day, hour, minute, second = obs_time.split("_")
         if 0 <= int(minute) < 15:
            qmin = "00"
         elif 15 <= int(minute) < 30: 
            qmin = "15"
         elif 30 <= int(minute) < 45: 
            qmin = "30"
         elif 45 <= int(minute) < 59: 
            qmin = "45"
         qtime = year + "_" + month + "_" + day + "_" + hour + "_" + qmin  

         metar_sum = [station_id, qtime, obs_time, observation_time, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, sea_level_pressure_mb, sky_conditions]
         #metar_html += obs_time + str(metar_sum) + "<br>"
         if qtime not in metar_dict:
            metar_dict[qtime] = {} 
            metar_dict[qtime]['stations'] = []
            metar_dict[qtime]['observation_times'] = []
            metar_dict[qtime]['temp_cs'] = []
            metar_dict[qtime]['dewpoint_cs'] = []
            metar_dict[qtime]['wind_dirs'] = []
            metar_dict[qtime]['wind_spds'] = []
            metar_dict[qtime]['pressures'] = []
            metar_dict[qtime]['sky_conditions'] = []
         metar_dict[qtime]['stations'].append(station_id)
         metar_dict[qtime]['observation_times'].append(observation_time)
         metar_dict[qtime]['temp_cs'].append(temp_c)
         metar_dict[qtime]['dewpoint_cs'].append(dewpoint_c)
         metar_dict[qtime]['wind_dirs'].append(wind_dir_degrees)
         metar_dict[qtime]['wind_spds'].append(wind_speed_kt)
         metar_dict[qtime]['pressures'].append(sea_level_pressure_mb)
         metar_dict[qtime]['sky_conditions'].append(sky_conditions)
          

      sql_snaps = """SELECT filename, station_id, camera_id, local_datetime_key, ai_final, samples_done 
               FROM ml_weather_snaps
              WHERE filename like ?
              ORDER BY filename desc
      """

      sql = """
         SELECT A.filename, A.station_id, A.camera_id, A.local_datetime_key, A.ai_final, A.samples_done,
                B.sun_status, B.forecast
           FROM ml_weather_snaps A
     INNER JOIN weather_conditions B
             ON A.local_datetime_key = B.local_datetime_key
          WHERE filename like ?
       ORDER BY filename DESC
         """

      svals = ["%" + date + "%"]
      self.weather_cur.execute(sql,svals)
      rows = self.weather_cur.fetchall()
      html_snap_archive = ""
      html_snap_archive += metar_html 
      data = []
      for row in rows:
         filename, station_id, camera_id, local_datetime_key, ai_final, samples_done, sun_status, forecast = row
         sort_key = filename.replace(station_id + "_", "").replace(camera_id + "_", "")
         min_key = sort_key.replace(".jpg", "")
         sort_key += "_" + camera_id
         data.append((filename, station_id, camera_id, local_datetime_key, ai_final, samples_done,sort_key,min_key,sun_status, forecast ))
      data = sorted(data, key=lambda x: x[6], reverse=True)
      last_min_key = None 
      last_metar_info = ""
      for row in data:
         filename, station_id, camera_id, local_datetime_key, ai_final, samples_done , sort_key,min_key, sun_status, forecast = row
         img_url = "/latest/" + date + "/" + row[0]

         if min_key in metar_dict:



            md = metar_dict[min_key]
            stations_val = ",".join(md['stations'])
            times_val = ",".join(md['observation_times'])
            temps_val = ",".join(map(str,md['temp_cs']))
            dew_val = ",".join(map(str,md['dewpoint_cs']))
            wind_val = ",".join(map(str,md['wind_dirs']))
            wind_sp_val = ",".join(map(str,md['wind_spds']))
            pres_val = ",".join(map(str,md['pressures']))

            sky_cond_vals = []
       
            if md['sky_conditions'] is not None and md['sky_conditions'] != "": 
               print("MD:", md['sky_conditions'])
               print("TYPE:", type(md['sky_conditions']))
               for list_items in md['sky_conditions']:
                  list_items = json.loads(list_items)
                  for item in list_items:
                     print("ITEM:", item) 
                     #odata = json.loads(item)
                     print("ITEM:", item['sky_cover']) 
                     sky_cond_vals.append( item['sky_cover'])

               cond_val = str(",".join(sky_cond_vals))
            else:
               cond_val = str(",".join(md['sky_conditions']))

            metar_info = """
              <table class="table table-bordered">
                 <tr>
                    <th>Stations</th>
                    <th>Times</th>
                    <th>Temps</th>
                    <th>Dew Points</th>
                    <th>Wind Dir</th>
                    <th>Wind Speed</th>
                    <th>Pressure</th>
                    <th>Condition</th>
                 </tr>
                 <tr>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                    <th>{:s}</th>
                 </tr>
              </table>
            """.format(stations_val, times_val, temps_val, dew_val, wind_val, wind_sp_val, pres_val, cond_val)
         else:
            metar_info = " NO METAR DATA FOR " + min_key
            metar_info = last_metar_info

         date_hdr = "<h5>MIN KEY = {:s}</h5>".format(min_key)
         if last_min_key is None:
            html_snap_archive += date_hdr + last_metar_info  + "<div>"
         elif last_min_key != min_key:
            html_snap_archive += "</div>" + date_hdr + last_metar_info + "<div>"
          

         img_html = "<img width=320 height=180 src=" + img_url + ">"   
         html_snap_archive += img_html
         last_min_key = min_key
         last_metar_info = metar_info
      img_html += "</div>"
      out = self.render_widget("snap_archive", "<a href=?cmd=snap_archive>Snap Archive</a>", html_snap_archive, 12)

      return(out)
   
   def weather_main(self, in_data=None):
      if in_data['cmd'] == "" or in_data['cmd'] is None:
         mout = self.weather_main_menu(in_data)
         out = mout
      elif in_data['cmd'] == "snap_archive":
         out = self.snap_archive(in_data)
      else:
         out = "Command not found." + in_data['cmd']

      template = self.env.get_template("default.html")
      tout = template.render(station_id=self.station_id, sidebar=self.render_side_nav(),DEFAULT_CONTENT=out, active_weather="active")
      return(tout)
