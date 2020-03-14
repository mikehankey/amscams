#!/usr/bin/python3
import time
import sys
import os
from lib.FileIO import cfe, load_json_file, save_json_file
from lib.UtilLib import calc_radiant 
from lib.WebCalib import HMS2deg

def sync_event(event_url):
   orbit_url = event_url + "orbit.txt" 
   event_data_url = event_url + "event.txt"
   el = event_data_url.split("/")
   event_id = el[-2]
   my_event_file = "events/" + event_id + "-event.txt"
   my_orbit_file = "events/" + event_id + "-orbit.txt"
   print(event_data_url)
   if cfe(my_event_file) == 0:
      cmd = "wget \"" + event_data_url + "\" -O " + my_event_file 
      print(cmd)
      os.system(cmd)
   if cfe(my_orbit_file) == 0:
      cmd = "wget \"" + orbit_url + "\" -O " + my_orbit_file
      print(cmd)
      os.system(cmd)

   fp = open(my_event_file, "r")
   event_lines = fp.readlines()
   fp.close()

   events = {}
   events[event_id] = {}

   for line in event_lines:
      if "beg ;" in line:
         start_lat,start_lon,start_alt = parse_lat_lon_alt(line)
      if "end ;" in line:
         end_lat,end_lon,end_alt = parse_lat_lon_alt(line)
      if "rad ;" in line:
         rad_ra, rad_dec, vel = parse_rad_vel(line)
      if "orb ;" in line:
         (a,e,i,omega,asc_node,vel_geo,vel_h,geo_ra,geo_dec,q_peri,true_anom) = parse_orb(line)
   events[event_id]['start_lat'] = start_lat
   events[event_id]['start_lon'] = start_lon
   events[event_id]['start_alt'] = start_alt
   events[event_id]['end_lat'] = end_lat 
   events[event_id]['end_lon'] = end_lon
   events[event_id]['end_alt'] = end_alt
   events[event_id]['rad_ra'] = rad_ra
   events[event_id]['rad_dec'] = rad_dec
   events[event_id]['vel'] = vel 
   events[event_id]['a'] = a 
   events[event_id]['e'] = e
   events[event_id]['i'] = i
   events[event_id]['omega'] = omega
   events[event_id]['asc_node'] = asc_node
   events[event_id]['vel_geo'] = vel_geo
   events[event_id]['geo_ra'] = geo_ra
   events[event_id]['geo_dec'] = geo_dec
   events[event_id]['q_peri'] = q_peri
   events[event_id]['true_anom'] = true_anom 

   print(events)
   mike_plot_bills_event(events[event_id], event_id)

def parse_orb(line):
   data = {}
   line = line.replace("orb ;", "")
   stuff = line.split() 
   for i in range(0, len(stuff)):
      if i % 3 == 0 or i == 0:
         key = stuff[i]
         value =  stuff[i+1]
         if i + 2 <= len(stuff) - 1:
            error = stuff[i+2]
         data[key] = value
         print("ORB:",key,value)

   a = data['a']
   e= data['e']
   i= data['incl']
   omega = data['omega']
   asc_node = data['asc_node']
   vel_geo = data['vel_g']
   vel_h = data['vel_h']
   geo_ra = data['alp_geo']
   geo_dec = data['del_geo']
   q_peri = data['q_per']
   true_anom = data['true_anom']

   return(a,e,i,omega,asc_node,vel_geo,vel_h,geo_ra,geo_dec,q_peri,true_anom)
     
def parse_rad_vel(line):
   data = {}
   line = line.replace("rad ;", "")
   stuff = line.split() 
   for i in range(0, len(stuff)):
      if i % 3 == 0 or i == 0:
         key = stuff[i]
         value =  stuff[i+1]
         if i + 2 <= len(stuff) - 1:
            error = stuff[i+2]
         data[key] = value
         print("VEL:",key,value)

   rad_ra = data['alp']
   rad_dec = data['del']
   vel= data['vel']
   return(rad_ra, rad_dec, vel)

def parse_lat_lon_alt(line):

   data = {}
   line = line.replace("beg ;", "")
   line = line.replace("end ;", "")
   stuff = line.split() 
   for i in range(0, len(stuff)):
      if i % 3 == 0 or i == 0:
         key = stuff[i]
         value =  stuff[i+1]
         error = stuff[i+2]
         data[key] = value
         print(key,value)
   lat = data['lat']
   lon = data['lon']
   alt = data['ht']
   return(lat,lon,alt)

def mike_plot_bills_event(event, event_id):
   #mike_orb_vars = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")
   end_lon = float(event['end_lon'])
   end_lat = float(event['end_lat'])
   end_alt = float(event['end_alt'])
   start_lon = float(event['start_lon'])
   start_lat = float(event['start_lat'])
   start_alt = float(event['start_alt'])
   vel = float(event['vel'])
   print(event_id)
   #20181205_023831A
   YY = event_id[0:4]
   MM = event_id[4:6]
   DD = event_id[6:8]
   HH = event_id[9:11]
   MIN = event_id[11:13]
   SEC = event_id[13:15]
   #arg_date, arg_time = event_id.split(" ")
   print(YY,MM,DD,HH,MIN,SEC)
   arg_date = YY + "-" + MM + "-" + DD 
   arg_time = HH + ":" + MIN + ":" + SEC 

   rad_rah,rad_dech,rad_az,rad_el,track_dist,entry_angle = calc_radiant(end_lon,end_lat,end_alt,start_lon,start_lat,start_alt, arg_date, arg_time)
   rad_rah = str(rad_rah).replace(":", " ")
   rad_dech = str(rad_dech).replace(":", " ")
   ra,dec = HMS2deg(str(rad_rah),str(rad_dech))

   print("RA:DEC", ra,dec,rad_az,rad_el)
   # run orbit
   metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")
   event_start_time = arg_date + "T" + arg_time
   metorb['orbit_vars']['meteor_input']['start_time'] = event_start_time
   metorb['orbit_vars']['meteor_input']['end_point'] = [end_lon,end_lat,end_alt]
   metorb['orbit_vars']['meteor_input']['rad_az'] = rad_az
   metorb['orbit_vars']['meteor_input']['rad_el'] = entry_angle
   metorb['orbit_vars']['meteor_input']['orad_ra'] = ra
   metorb['orbit_vars']['meteor_input']['orad_dec'] = dec 
   metorb['orbit_vars']['meteor_input']['velocity'] = vel


   save_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json",metorb)
   os.system("cd /home/ams/amscams/pythonv2/; ./mikeOrb.py ")
   time.sleep(1)
   new_metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")
   metorb = new_metorb
   mikes_data = {}
   mikes_data['rad_ra'] = metorb['orbit_vars']['meteor_input']['rad_ra']
   mikes_data['rad_dec'] = metorb['orbit_vars']['meteor_input']['rad_dec']
   mikes_data['vel'] = metorb['orbit_vars']['meteor_input']['velocity']
   mikes_data['a'] = metorb['orbit_vars']['final_orbit_plot']['a']
   mikes_data['e'] = metorb['orbit_vars']['final_orbit_plot']['e']
   mikes_data['I'] = metorb['orbit_vars']['final_orbit_plot']['I']
   mikes_data['M'] = metorb['orbit_vars']['final_orbit_plot']['M']
   #Omega
   mikes_data['Omega'] = metorb['orbit_vars']['final_orbit_plot']['Peri']
   mikes_data['asc_node'] = metorb['orbit_vars']['final_orbit_plot']['Node']
   mikes_data['q_peri'] = metorb['orbit_vars']['final_orbit_plot']['q']

   mikes_data['event_time_utc'] = metorb['orbit_vars']['final_orbit_plot']['event_time_utc']
   mikes_data['jd_at_t'] = metorb['orbit_vars']['final_orbit_plot']['jd_at_t']

   metorb['bills_data'] = event
   metorb['mikes_data'] = mikes_data
   mike_bill_file = "events/" + event_id + "-mike-bill.json"
   save_json_file(mike_bill_file, metorb)
   print(metorb)

event_url = sys.argv[1]
sync_event(event_url)


