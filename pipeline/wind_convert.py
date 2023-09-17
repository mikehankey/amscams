from flask import Flask, request, Response, make_response
import math
from sympy import Point3D, Line3D
import json 
import numpy as np
import os
import pymap3d as pm
from trianglesolver import solve, degree
from lib.PipeUtil import load_json_file, save_json_file, dist_between_two_points
app = Flask(__name__, static_url_path='/static')

def get_bearing(lat1, long1, lat2, long2):
    dLon = (long2 - long1)
    x = math.cos(math.radians(lat2)) * math.sin(math.radians(dLon))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
    brng = np.arctan2(x,y)
    brng = np.degrees(brng)

    return brng


def compute_zenith_angle_and_heading(slat,slon,salt,elat,elon,ealt):

   side_a = (salt - ealt) / 1000
   side_b = dist_between_two_points(slat,slon,elat,elon)
   side_c = math.sqrt((side_a ** 2) + (side_b ** 2))

   # sides / angles
   a,b,c,A,B,C = solve(b=side_b, a=side_a, c=side_c)

   azimuth_heading = get_bearing(slat, slon, elat, elon)
   if azimuth_heading < 0:
      azimuth_heading += 360

   zenith_angle = A / degree
   za = 90 - zenith_angle

   return(za, azimuth_heading)

def track_points(sp, ep):
   wgs84 = pm.Ellipsoid('wgs84');
   slat,slon,salt = sp
   elat,elon,ealt = ep 
   print("S", type(slat),type(slon),type(salt))
   print("E", elat,elon,ealt) 

   
   #x1, y1, z1 = pm.geodetic2ecef(slat, slon, salt, wgs84)
   #x2, y2, z2 = pm.geodetic2ecef(float(elat), float(elon), float(ealt), wgs84)
   # lower are sides UPPER are angles
   #p1 = Point3D(x1,y1,z1)
   #p2 = Point3D(x2,y2,z2)
   #hyp_dist = p1.distance(p2)
   #print("DIST:", hyp_dist)
   #a,b,c,A,B,C = solve(b=7, A=5*degree, B=70*degree)
   #print(C / degree)

   # find sides and angles of track A = height, B=Adjacent, C=Hyponenous

def save_json_file(json_file, json_data):
   compress = False
   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True )
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()

def make_config(project_name,mass,rock_density,lat,lon,alt, terminal_speed, heading_azimuth, zenith_angle, exposure_time):
   dfm_config= """
[met]
name={:s}
#mass kg
mass0={:s}
#rock rock density, kgm-3
#rdens0=3500.0
rdens0={:s}
#terminal lat, degrees
lat0={:s}
#uncertainty in latitude, degrees
dlat=0.0008
#terminal lon, degrees
lon0={:s}
#uncertainty in longitude, degrees
dlon=0.0008
#terminal height, m
z0={:s}
#uncertainty in terminal height, m
dz=100
#terminal speed, ms-1
vtot0={:s}
#uncertainty in end speed, ms-1
dvtot=300
#zenith angle of proj path, aka zenith distance
zenangle={:s}
#uncertainty in zenith angle
dzenith=0.02
#azimuth of trajectory at end point, degrees
azimuth0={:s}
#uncertainty in azimuth direction, degrees
dazimuth0=0.02
exposure_time={:s}

[gnd]
#atmospheric profile data file
atmosprofile=./{:s}_wind.csv
gndlvl=-15.0

""".format(str(project_name),str(mass),str(rock_density),str(lat),str(lon),str(alt), str(terminal_speed), str(heading_azimuth), str(zenith_angle), str(exposure_time),str(project_name))


#[montecarlo]
#no_runs = 0 
#dmass = 0.5
#drdens = 5
#dragmin = 0.0
#dragmax = 0.3
#dwind = 5.0
#global scaling factor
#rand = 1.0

   return(dfm_config)

@app.route('/', methods=['GET', 'POST'])
def main_wind_convert():
   
   proj_id = request.args.get("id")
   if proj_id is not None:
      print("PROJ ID:", proj_id)
      proj_dir = "DFM/" + proj_id + "/" 
      proj_file = proj_dir + proj_id + ".json"
      print("proj_file:", proj_file)
      if os.path.exists(proj_file):
         jd = load_json_file(proj_file)
         print("KEYS:", jd.keys())
   else:
      # initialize the data container
      jd = {}
      fields = ["project_name", "mass", "rock_density", "slat", "slon", "salt", "elat", "elon", "ealt", "heading_azimuth", "zenith_angle", "terminal_speed", "exposure_time", "src_data", "format_type", "reverse_wind_dir", "wind_speed_src_units", "press_units"]
      for field in fields:
         jd[field] = ""

   out = """
   <a href=https://rucsoundings.noaa.gov/>Sounding Data</a><br>
   <form method=post action=post_data>
      <h2>Enter Meteor Properties</h2>
       Project Name <input type=text name="project_name" value="{:s}"> <br>
       Starting Mass <input type=text name="mass" value="{:s}"> <br>
       Rock Density <input type=text name="rock_density" value="{:s}"> <br>
       Start Lat <input type=text name="slat" value="{:s}"> <br>
       Start Lon <input type=text name="slon" value="{:s}"> <br>
       Start Alt <input type=text name="salt" value="{:s}"> <br>
       End Lat <input type=text name="elat" value="{:s}"> <br>
       End Lon <input type=text name="elon" value="{:s}"> <br>
       End Alt <input type=text name="ealt" value="{:s}"> <br>
       Heading <input type=text name="heading_azimuth" value="{:s}"> <br>
       Zenith Angle <input type=text name="zenith_angle" value="{:s}"> <br>
       Terminal Vel <input type=text name="terminal_speed" value="{:s}"> m/s<br>
       Exposure Time <input type=text name="exposure_time" value="{:s}"> (2023-01-20T09:38:58) <br>
       Select Source Wind Format <ul>
       """.format(str(jd['project_name']), str(jd['mass']), str(jd['rock_density']), str(jd['slat']), str(jd['slon']), str(jd['salt']), str(jd['elat']), str(jd['elon']), str(jd['ealt']), str(jd['heading_azimuth']), str(jd['zenith_angle']), str(jd['terminal_speed']), str(jd['exposure_time']))

   if jd['format_type'] == "NOAA1":
      noaa1_format = "CHECKED"
   else:
      noaa1_format = ""
   if jd['format_type'] == "NOAA2":
      noaa2_format = "CHECKED"
   else:
      noaa2_format = ""
   if jd['format_type'] == "EU1":
      eu1_format = "CHECKED"
   else:
      eu1_format = ""


   if jd['reverse_wind_dir'] == "1":
      rwd = "CHECKED"
   else:
      rwd = ""
   ws_knots, ws_ms, ws_ms10 = "","",""
   press_units_100 ,press_units_1000 = "", ""

   if jd['wind_speed_src_units'] == "knots":
      ws_knots = "CHECKED"
   if jd['wind_speed_src_units'] == "ms":
      ws_ms = "CHECKED"
   if jd['wind_speed_src_units'] == "ms10":
      ws_ms10 = "CHECKED"

   if "press_units" in jd: 
      if jd['press_units'] == "hpa100":
         press_units_100 = "CHECKED"
         press_units_1000 = ""

      if jd['press_units'] == "hpa1000":
         press_units_100 = "CHECKED"
         press_units_1000 = ""
   else:
      press_units_100 = "CHECKED"
      press_units_1000 = ""
  
   print("FORMAT:", jd['format_type'])
   print("WS UNITS:", jd['wind_speed_src_units'])

   out += """
          <input {:s} type=radio name=format value="NOAA1"> NOAA Format 1 -- 7 Fields , RID pressure, height, temp_c10 temp_dp_c10 wind dir, wind speed <br>

          <input {:s} type=radio name=format value="NOAA2"> NOAA Format 2 -- 11 Fields , MB pressure, C temps, Knots Wind <br>
          <input {:s} type=radio name=format value="EU1"> EU Format 1 -- 6 Fields Height hpa, Press, Temp C, Rel Hum WDir Wind Speed m/3
       </ul>
       Source Wind Speed Units
       <ul>
          <input type=radio {:s} name=wind_speed_src_units value="knots"> knots<br>
          <input type=radio {:s} name=wind_speed_src_units value="ms"> m/s<br>
          <input type=radio {:s} name=wind_speed_src_units value="ms10"> 10 * m/s <br>
       </ul>
       <ul>
       <input {:s} type=checkbox name=reverse_wind_dir value="1"> Reverse Wind Direction 
       </ul>


      """.format(noaa1_format, noaa2_format, eu1_format, ws_knots, ws_ms, ws_ms10, rwd)
   out += """
       Source Pressure Units
       <ul>
          <input type=radio {:s} name=press_units value="hpa100"> hpa *100<br>
          <input type=radio {:s} name=press_units value="hpa1000"> hpa *1000<br>
       </ul>
   """ .format(press_units_100, press_units_1000)


   out += """
      <h2>Enter sounding data below</h2>
      <textarea rows=20 cols=120 name="sounding_data" >
      {:s}
      </textarea>
      <br>
      <input type=submit value="continue">
   </form> 
   """.format(str(jd['src_data']))


   return(out)


@app.route('/post_data', methods=['GET', 'POST'])
def post_data():
   dfn_dir = "/home/ams/DFN_darkflight/DFN_darkflight/"
   # get values for base config
   config_data = {}
   format_type = request.form.get("format")
   wind_speed_src_units = request.form.get("wind_speed_src_units")
   reverse_wind_dir = request.form.get("reverse_wind_dir")
   project_name = request.form.get("project_name")
   mass = request.form.get("mass")
   rock_density = request.form.get("rock_density")
   slat = float(request.form.get("slat"))
   slon = float(request.form.get("slon"))
   salt = float(request.form.get("salt"))
   elat = float(request.form.get("elat"))
   elon = float(request.form.get("elon"))
   ealt = float(request.form.get("ealt"))
   press_units = request.form.get("press_units")
   terminal_speed = request.form.get("terminal_speed")
   zenith_angle = request.form.get("zenith_angle")
   exposure_time = request.form.get("exposure_time")
   heading_azimuth = request.form.get("heading_azimuth")
   dfn_config = make_config(project_name,mass,rock_density,elat,elon,ealt, terminal_speed, zenith_angle, heading_azimuth, exposure_time)
   config_data['format_type'] = format_type
   config_data['reverse_wind_dir'] = reverse_wind_dir
   config_data['project_name'] = project_name 
   config_data['mass'] = mass
   config_data['rock_density'] = rock_density
   config_data['slat'] = slat
   config_data['slon'] = slon
   config_data['salt'] = salt
   config_data['elat'] = elat
   config_data['elon'] = elon
   config_data['ealt'] = ealt
   config_data['terminal_speed'] = terminal_speed
   config_data['zenith_angle'] = zenith_angle
   config_data['heading_azimuth'] = heading_azimuth
   config_data['exposure_time'] = exposure_time
   config_data['dfn_config'] = dfn_config
   config_data['wind_speed_src_units'] = wind_speed_src_units

   proj_dir = "/home/ams/amscams/pipeline/DFM/" + project_name.replace(" ", "") + "/"
   if os.path.exists(proj_dir) is False:
      os.makedirs(proj_dir)

   #print(slat,slon,salt)
   #print(elat,elon,ealt)

   za, bearing = compute_zenith_angle_and_heading(slat,slon,salt,elat,elon,ealt)
   print("________________________")
   print("ZA BEAR:", za, bearing)
   print("________________________")

   #track_points((slon, slat,salt), (elon,elat,ealt))
     
   src_data = request.form.get("sounding_data")

   config_data['src_data'] = src_data 

   lines = src_data.split("\n")

   out = ""

   source = "<table border=1>"
   if format_type == "EU1":
      source += "<tr><td>HEIGHT (m)</td><td>PRESS (hPa)</td><td>TEMP (c)</td><td>REL HUM</td><td>WIND DIR</td><td>WIND SPEED (m/s)</td></tr>"

   elif format_type == "NOAA2":
      source += "<tr><td>PRES (hpa)</td><td>HGHT (m)</td><td>TEMP (C)</td><td>DWPT (C)</td><td>RELH (%)</td><td>MIXR (g/kg)</td><td>DRCT (deg)</td><td>SKNT (knots)</td></tr>"
   elif format_type == "NOAA1":
      source += "<tr><td>PRES (hpa)</td><td>HGHT (m)</td><td>TEMP (C)</td><td>DWPT (C)</td><td>WIND DIR(deg)</td><td>WIND SPEED ({:s}</td></tr>".format(config_data['wind_speed_src_units'])


   # Height,   TempK,   Press,    RHum,    Wind,   WDir
   wind_model = "<table border=1>"
   wind_model += "<tr><td>Height (m)</td><td>Temp (K)</td><td>Press (p)</td><td>RHum</td><td>Wind Speed (m/s)</td><td>WDir</td></tr>"

   #dfn_data = "#HEIGHT,TEMPK,PRESSURE,RHUM,WIND_SPD,WIND_DIR\n"
   dfn_data = "#Height, TempK, Press, RHum, Wind, WDir\n"
   if reverse_wind_dir == 1 or reverse_wind_dir == "1":
      reverse_direction = True
   else:
      reverse_direction = False 

   data_lines = []
   for line in lines:
      if len(line) == 0:
         continue
      if line[0] == "#":
         continue
      if "\r\n" in line:
         line = line.replace("\r\n", "")
      elif "\r" in line:
         line = line.replace("\r", "")
      else:
         line = line.replace("\n", "")
      # format 1 -- USA from Ken 11 fields
      #   PRES   HGHT   TEMP   DWPT   RELH   MIXR   DRCT   SKNT   THTA   THTE   THTV
      #    hPa     m      C      C      %    g/kg    deg   knot     K      K      K
      line = line.replace("  ", " ")
      line = line.replace("  ", " ")
      line = line.replace("  ", " ")
      if line[0] == " ":
         line = line[1:]
      elm = line.split(" ")
      if "9999" in line:
         continue
      if format_type == "EU1":
         
         data = line.split(",")
         print("DATA:", data)
         height = float(data[0])
         pressure = float(data[1]) 

         if press_units == "hpa1000":
            new_pressure = float(data[1]) * 1000
         else:
            new_pressure = float(data[1])  * 100
         print("PRESS UNITS", press_units, pressure)

         temp_c = float(data[2]) 
         relh = float(data[3]) 
         wind_dir = float(data[4])
         wind_speed = float(data[5])
         wind_speed_ms = wind_speed
         temp_k = round(temp_c + 273.15, 2)

         if relh < 1:
            relh = relh * 100

         if True:
            if reverse_direction is True: 
               wind_dir_new = float(wind_dir) - 180
            else:
               wind_dir_new = float(wind_dir )
            if wind_dir_new < 0:
               wind_dir_new += 360


         source += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>\n".format(str(height), str(pressure), str(temp_c), str(relh), str(wind_dir), str(wind_speed))
         wind_model += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed), str(wind_dir_new))
         dfn_line = "{:s}, {:s}, {:s}, {:s}, {:s}, {:s}\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed_ms), str(wind_dir_new) )
         dfn_data += dfn_line
         data_lines.append(dfn_line)

      if format_type == "NOAA1":
         data = line.split(" ")
         if data[0] == "4" or data[0] == "5" or data[0] == "6":
            pressure = float(data[1]) 
            new_pressure = float(data[1]) * 10
            height = float(data[2])
            temp_c_10 = int(data[3]) * .1
            temp_dp_c_10 = int(data[4])  * .1
            temp_k = round(temp_c_10 + 273.15, 2)
            temp_c = round(temp_c_10,2)
            temp_dp_c = round(temp_dp_c_10,2)
            wind_dir = float(data[5])
            wind_speed = float(data[6])
            if reverse_direction is True: 
               wind_dir_new = float(wind_dir) - 180
            else:
               wind_dir_new = float(wind_dir )
            if wind_dir_new < 0:
               wind_dir_new += 360
            #print("WIND DIR:", reverse_direction, wind_dir, wind_dir_new)

            relh= temp_c_10 - temp_dp_c_10
            relh = relh * 5
            relh = round(100 - relh , 2)
            #relh = relh / 100

            if relh < 0:
               relh = 0

            print(height, temp_k, pressure, relh, wind_dir, wind_speed)
            if wind_speed_src_units == "ms10":
               wind_speed_ms = round(wind_speed * .1,2)
            elif wind_speed_src_units == "knots":
               wind_speed_ms = round(float(wind_speed_knots) * .51444 ,2)
            else:
               wind_speed_ms = round(wind_speed,2)

            source += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>\n".format(str(pressure), str(height), str(temp_c), str(temp_dp_c), str(wind_dir), str(wind_speed))
            wind_model += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed_ms), str(wind_dir_new))
            dfn_line = "{:s}, {:s}, {:s}, {:s}, {:s}, {:s}\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed_ms), str(wind_dir_new) )
            dfn_data += dfn_line
            data_lines.append(dfn_line)

      if format_type == "NOAA2" and len(elm) == 11:
         line = line.replace(" ", ",")
         pressure, height, temp, dwpt, relh, mixr, wind_dir, wind_speed_knots, thta_k,thte_k, thtv_k = line.split(",")
         if "PRES" in line or float(wind_speed_knots) <= 0:
            out += line + "<br>"
            #source += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format(str(pressure), str(height), str(temp), str(dwpt), str(relh), str(mixr), str(wind_dir), str(wind_speed_knots))
            continue
         relh = float(relh) #/ 100
         if relh < 0:
            relh = 0
         if relh > 1.1:
            relh = relh / 100

         if press_units == "hpa1000":
            new_pressure = round(float(pressure) * 1000,2)
         elif press_units == "hpa100":
            new_pressure = round(float(pressure) * 100,2)
         else:
            new_pressure = round(float(pressure) * 1,2)

         #temp_c_10 = float(temp) * .1
         temp_c = round(float(temp),2)
         temp_dwpt_c_10 = float(dwpt) * .1
         wind_dir = round(float(wind_dir),2)

         # is this 0-1 or 0-100 ???
         # example murrili is 0-100
         #relh = float(relh) / 100

         temp_k = round(temp_c + 273.15, 2)
         wind_speed_ms = round(float(wind_speed_knots) * .51444 ,2)
         # must be squared! kn/s = 0.514444444 m/s2.
         #wind_speed_ms = wind_speed_ms ** 2
         if reverse_direction == True:
            wind_dir_new = wind_dir - 180
         else:
            wind_dir_new = wind_dir 
         if wind_dir_new < 0:
            wind_dir_new += 360

         out += line 
         #print("PRE", pressure)
         # Height,   TempK,   Press,    RHum,    Wind,   WDir
         wind_icon = "<img src=https://archive.allsky.tv/APPS/icons/arrow-up.png width={:s} height={:s} style='transform: rotate({:s}deg);'>".format(str(int(wind_speed_knots)), str(int(wind_speed_knots)), str(int(wind_dir-180)))
         wind_icon_dfn = "<img src=https://archive.allsky.tv/APPS/icons/arrow-up.png width={:s} height={:s} style='transform: rotate({:s}deg);'>".format(str(int(wind_speed_ms*1.94)), str(int(wind_speed_ms*1.94)), str(int(wind_dir_new)))

         source += "<tr style='height:50px'><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s} {:s}</td><td>{:s}</td></tr>\n".format(str(pressure), str(height), str(temp), str(dwpt), str(relh), str(mixr), str(wind_dir), str(wind_icon), str(wind_speed_knots))
         wind_model += "<tr style='height: 50px'><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s} {:s}</td></tr>\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed_ms), str(wind_dir_new), wind_icon_dfn)
         dfn_line = "{:s}, {:s}, {:s}, {:s}, {:s}, {:s}\n".format(str(height), str(temp_k), str(new_pressure), str(relh), str(wind_speed_ms), str(wind_dir_new) )
         dfn_data += dfn_line
         data_lines.append(dfn_line)
   source += "</table>"
   wind_model += "</table>"

   out = """<table border=1>
   <tr><td>{:s}</td><td>{:s}</td></tr>
   <tr><td>{:s}</td><td>{:s}</td></tr>
   </table>""".format("SOURCE WIND DATA", "DFN WIND DATA", source, wind_model)

   config_data['wind_model'] = dfn_data 

   json_file = proj_dir + "/" + project_name + ".json"

   save_json_file(json_file, config_data)
   #run_dir = proj_dir + "/run/base/"
   #if os.path.exists(run_dir) is False:
   #   os.makedirs(run_dir)
   c = 0
   print("DATA LINES:", len(data_lines))
   if len(data_lines) > 100:
      dfn_data = ""
      skip = int(len(data_lines) / 100)
      print("SKIP:", skip)
      for line in data_lines:
         if c % skip == 0:
            dfn_data += line 
            print("USE:", c, line)
         else:
            print("SKIP:", c)

         c += 1

   out += "DFN Wind Data File <pre>{:s}</pre>".format(dfn_data)
   out += "<hr>DFN Config<pre>{:s}</pre>".format(dfn_config)

   # save base config and wind files
   fp = open(proj_dir + "/" + project_name + ".cfg", "w")
   fp_wind = open(proj_dir + "/" + project_name + "_wind.csv", "w")
   fp.write(dfn_config)
   fp_wind.write(dfn_data)

   # make commands for many runs
   #python3 ./DFN_DarkFlight.py -e ./2023_01_20.cfg -w ./2023_01_20_wind.csv
   # do base run first. 
   cmd = "python3 " + dfn_dir  + "DFN_DarkFlight.py -e " + proj_dir + project_name + ".cfg -w " + proj_dir + project_name + "_wind.csv -K " + project_name 
   print(cmd)

   # change the zenith angle +/- 25 degrees in 5 degree icrements
   # change the heading azimuth +/- 10 degrees in 2 degree icrements
   # change the velocity between 3000 and 6000 in 1000 icrements
   # move up and down the trajectory in 2km increments around end point 2 or 3 x
   # change the end lon +/- .05 degree (aprox 11 km)
   # change the end lat +/- .05 degree (aprox 11 km)
   cmd = "python3 track_points.py " + project_name
   print(cmd)
   #os.system(cmd)
   #track_points((slon,slat,salt),(elon,elat,ealt))

   return(out)
