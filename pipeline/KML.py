#!/usr/bin/python3

import sys
import simplekml
from lib.PipeUtil import cfe, load_json_file


def point_from_bearing(p1, brng, d):
    lon1, lat1 = p1
    print("START:", p1)
    print("HEADING:", brng)
    print("DISTANCE:", d)
    brng = math.radians(brng)
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    R = 6378.1 #Radius of the Earth
    # brng = 1.57 #Bearing is 90 degrees converted to radians.
    # d = 15 #Distance in km
    lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
       math.cos(lat1)*math.sin(d/R)*math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    print("END:", lon2,lat2)
    return(lon2,lat2)


def map_event(meteor_file): 
   mj = load_json_file(meteor_file)
   # lon,lat,desc
   points = []
   # lon1,lat1,alt1,lon2,lat2,alt2,desc
   lines = []
   if "multi_station_event" in mj:
      obs = mj['multi_station_event']['obs']
   else:
      print("No MSE can't map.")
      return()
   if "solutions" in mj:
      solutions = mj['solutions']
   else:
      print("NO SOLUTIONS!")
      solutions = []
   obs_loc = {}
   for station in obs:
      for obsf in obs[station]:
         lat,lon,alt = obs[station][obsf]['loc'] 
         obs_loc[station] = [lat,lon,alt]
         points.append((lon,lat,station))
   for data in solutions:
      station_key, lat1,lon1,alt1,lat2,lon2,alt2,dist,dur,vel = data 
      ob1, ob2 = station_key.split("_")
      s1,c1 = ob1.split("-")
      s2,c2 = ob2.split("-")
      sol_desc = s1 + "_" + s2
      lines.append((lon1,lat1,alt1,lon2,lat2,alt2,sol_desc)) 
      lat,lon,alt = obs_loc[s2]
      lines.append((lon,lat,alt,lon1,lat1,alt1,"vectstart" + s2)) 
      lines.append((lon,lat,alt,lon2,lat2,alt2,"vectend" + s2)) 
   print(points)
   print(lines)
   make_kml(meteor_file,points,lines)

def make_kml(meteor_file, points, lines):
   kml_file = meteor_file.replace(".json", ".kml")
   kml = simplekml.Kml()
   used = {}

   pc = 0
   colors = ['ff0b86b8', 'ffed9564', 'ff0000ff', 'ff00ffff', 'ffff0000', 'ff00ff00', 'ff800080', 'ff0080ff', 'ff336699', 'ffff00ff' ]
   for point in points:
      lon,lat,station = point
      if station not in used: 
         color = colors[pc]
         pnt = kml.newpoint(name=station, coords=[(lon,lat)])
         pnt.description = station
         pnt.style.labelstyle.color=color
#simplekml.Color.darkgoldenrod 
         pnt.style.labelstyle.scale = 1
         pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
         pnt.style.iconstyle.color=color 

         used[station] = 1
         pc += 1
   linestring = {}
   lc = 0
   for line in lines:
      (lon1,lat1,alt1,lon2,lat2,alt2,line_desc) = line
      if "vect" in line_desc:
         linestring[lc] = kml.newlinestring(name="")
      else:
         linestring[lc] = kml.newlinestring(name=line_desc)
      linestring[lc].coords = [(lon1,lat1,alt1),(lon2,lat2,alt2)]
      linestring[lc].altitudemode = simplekml.AltitudeMode.relativetoground

      if "vect" not in line_desc:
         linestring[lc].extrude = 0
         linestring[lc].style.linestyle.color=simplekml.Color.red

         linestring[lc].style.linestyle.width=3

      else:
         print("BLUE!")
         linestring[lc].extrude = 0
         if "end" in line_desc:
            linestring[lc].style.linestyle.color=simplekml.Color.goldenrod
         else:
            linestring[lc].style.linestyle.color=simplekml.Color.darkgoldenrod
      lc += 1
   kml.save(kml_file)
   print("saved", kml_file)


mf = sys.argv[1]
map_event(mf)
