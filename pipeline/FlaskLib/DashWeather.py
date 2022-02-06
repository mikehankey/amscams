from FlaskLib.Dashboard import Dashboard
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
      
   def weather_main(self, in_data=None):
      if in_data['cmd'] == "" or in_data['cmd'] is None:
         mout = self.weather_main_menu(in_data)
         out = mout
      else:
         out = "Command not found." + in_data['cmd']

      template = self.env.get_template("default.html")
      tout = template.render(station_id=self.station_id, sidebar=self.render_side_nav(),DEFAULT_CONTENT=out, active_weather="active")
      return(tout)
