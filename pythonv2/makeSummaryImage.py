#!/usr/bin/python3

import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import os
import sys
import glob
#import cv2
from PIL import Image, ImageDraw, ImageFont
from FileIO import load_json_file, save_json_file, todict,cfe


def plot_reductions(job_dir, job_file, json_data):
   as6 = json_data['as6_info']
   for key in as6:
      if "reduced" in key:
         xs = []
         ys = []
         station_id = as6[key]['station_id']
         fd = as6[key]['all_red']['meteor_frame_data']
         for meteor_frame_time_str,fn,hd_x,hd_y,w,h,max_px,ra,dec,az,el in fd:
            print(hd_x,hd_y)
            xs.append(hd_x)
            ys.append(hd_y)
         plt.plot(xs,ys,'ro')
         min_x = min(xs) - 50
         max_x = max(xs) + 50
         min_y = min(ys) - 50
         max_y = max(ys) + 50
         plt.title('Reduction Points for ' + str(station_id))
         plt.axis([min_x,max_x,max_y,min_y])
         plt.savefig(job_dir + job_file + "-RED-" + station_id + ".png")
         plt.cla()

def caption_image(img_file, title, caption, caption2 = "", caption3 = ""):

   img_pil = Image.open(img_file).convert('LA')
   img_pil.resize((384,216), Image.ANTIALIAS)
   rgb_img_pil = Image.new("RGBA", img_pil.size)
   rgb_img_pil.paste(img_pil)
   img_w = rgb_img_pil.size[0]
   img_h = rgb_img_pil.size[1]
   print("MIKE:", img_w, img_h)

   fig_w = img_w / 72
   fig_h = img_h / 72

   #fig = plt.figure(figsize=(fig_w,fig_h))
   fig = plt.figure()
   columns = 1
   rows = 1
   ax = []


   img = np.asarray(rgb_img_pil)
   ax.append(fig.add_subplot(rows,columns,1))
   ax[0].set_title(title, loc='center')
   ax[0].set_anchor('W')

   ax[0].get_xaxis().set_visible(False)
   ax[0].get_yaxis().set_visible(False)
   plt.imshow(img)
   #print(fig_w, fig_w/10)
   plt.figtext(fig_w/10,.08,caption, wrap=False, horizontalalignment='center',fontsize=12)
   plt.figtext(fig_w/10,.04,caption2, wrap=False, horizontalalignment='center',fontsize=12)

   #plt.figtext(fig_w/10,0,caption3, wrap=False, horizontalalignment='center',fontsize=12)
   fig_file = img_file.replace(".png", "-caption.png", )
   plt.tight_layout(pad=0)
   print("FIG FILE:", fig_file, fig_w,fig_h)
   fig.savefig(fig_file, dpi=72)

def make_summary_text(job_dir, job_file):
   json_file = job_dir + job_file + ".json"
   json_data = load_json_file(json_file)
   print(json_data)


if __name__ == "__main__":

   deg = u"\u00b0"
   
   job_dir = sys.argv[1]
   thumb_dir = job_dir + "/thumbs/"
   el=job_dir.split("/")
   job_file = el[1]
   json_file = job_dir + job_file + ".json"
   print("JSON:", json_file)
   json_data = load_json_file(json_file)
   station_data = load_json_file("stations.json")

   orb = json_data['orbit']
   print(orb)
   
   cmd = "rm " + job_dir + "*mike*.png"
   print(cmd)
   os.system(cmd)

   plot_reductions(job_dir, job_file, json_data) 

   cmd = "mogrify -format png -path " + job_dir + "thumbs/" + " -resize 400x400 " + job_dir + "*.png"
   print(cmd)
   os.system(cmd)


   # make headers
   head1 = Image.new('RGB', (1000,270), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
   d = ImageDraw.Draw(head1)
   d.text((10,10), "Video Meteor Summary", font=fnt, fill=(0,0,0))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
   d.text((12,60), "Event Information " , font=fnt, fill=(0,0,0))
   d.text((360,60), "Orbit " , font=fnt, fill=(0,0,0))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
   d.text((12,80), "Event Date Time: " , font=fnt, fill=(0,0,0))
   d.text((130,80), "{:s}".format(json_data['as6_info']['event_utc'])[0:-4], font=fnt, fill=(0,0,0))
   d.text((12,100), "Start Point:     " , font=fnt, fill=(0,0,0))
   d.text((130,100), "{:s}{:s}N {:s}{:s}W {:s}m ".format(str(math.degrees(json_data['rbeg_lat']))[0:6], deg, str(math.degrees(json_data['rbeg_lon']))[0:6], deg, str(json_data['rbeg_ele'])[0:8]), font=fnt, fill=(0,0,0))
   d.text((12,120), "End Point:      " , font=fnt, fill=(0,0,0))
   d.text((130,120), "{:s}{:s}N {:s}{:s}W {:s}m ".format(str(math.degrees(json_data['rend_lat']))[0:6], deg, str(math.degrees(json_data['rend_lon']))[0:6], deg, str(json_data['rend_ele'])[0:8]), font=fnt, fill=(0,0,0))
   d.text((12,140), "Velocity:       " , font=fnt, fill=(0,0,0))
   d.text((130,140), "{:s} KM/Second".format(str(json_data['v_init']/1000)[0:6]), font=fnt, fill=(0,0,0))

   d.text((360,80), "La Sun:" , font=fnt, fill=(0,0,0))
   if orb['la_sun'] is not None:
      d.text((440,80), "{:f}".format(orb['la_sun']) , font=fnt, fill=(0,0,0))
   d.text((360,100), "a:" , font=fnt, fill=(0,0,0))
   if orb['a'] is not None:
      d.text((440,100), "{:f}".format(orb['a']) , font=fnt, fill=(0,0,0))
   d.text((360,120), "e:" , font=fnt, fill=(0,0,0))
   if orb['e'] is not None:
      d.text((440,120), "{:f}".format(orb['e']) , font=fnt, fill=(0,0,0))
   d.text((360,140), "i:" , font=fnt, fill=(0,0,0))
   if orb['i'] is not None:
      d.text((440,140), "{:f}".format(orb['i']) , font=fnt, fill=(0,0,0))
   d.text((360,160), "peri:" , font=fnt, fill=(0,0,0))
   if orb['peri'] is not None:
      d.text((440,160), "{:f}".format(orb['peri']) , font=fnt, fill=(0,0,0))
   d.text((360,180), "node:" , font=fnt, fill=(0,0,0))
   if orb['node'] is not None:
      d.text((440,180), "{:f}".format(orb['node']) , font=fnt, fill=(0,0,0))
   d.text((360,200), "Pi:" , font=fnt, fill=(0,0,0))
   if orb['pi'] is not None:
      d.text((440,200), "{:f}".format(orb['pi']) , font=fnt, fill=(0,0,0))
   d.text((360,220), "q:" , font=fnt, fill=(0,0,0))
   if orb['q'] is not None:
      d.text((440,220), "{:f}".format(orb['q']) , font=fnt, fill=(0,0,0))

   d.text((550,80), "f:" , font=fnt, fill=(0,0,0))
   # ?? d.text((430,140), "{:f}".format(orb['q']) , font=fnt, fill=(0,0,0))
   d.text((550,100), "M:" , font=fnt, fill=(0,0,0))
   if orb['mean_anomaly'] is not None:
      d.text((620,100), "{:s}".format(str(orb['mean_anomaly'])) , font=fnt, fill=(0,0,0))
   d.text((550,120), "Q:" , font=fnt, fill=(0,0,0))
   if orb['Q'] is not None:
      d.text((620,120), "{:f}".format(orb['Q']) , font=fnt, fill=(0,0,0))
   d.text((550,140), "n:" , font=fnt, fill=(0,0,0))
   if orb['n'] is not None:
      d.text((620,140), "{:f}".format(orb['n']) , font=fnt, fill=(0,0,0))
   d.text((550,160), "T:" , font=fnt, fill=(0,0,0))
   if orb['T'] is not None:
      d.text((620,160), "{:s}".format(str(orb['T'])) , font=fnt, fill=(0,0,0))
   d.text((550,180), "Last Peri:" , font=fnt, fill=(0,0,0))
   if orb['last_perihelion'] is not None:
      d.text((620,180), "{:s}".format(orb['last_perihelion']) , font=fnt, fill=(0,0,0))
   d.text((550,200), "Tj:" , font=fnt, fill=(0,0,0))
   if orb['Tj'] is not None:
      d.text((620,200), "{:f}".format(orb['Tj']) , font=fnt, fill=(0,0,0))


#Orbit:
#  La Sun =  16.826343 deg
#  a      =   2.521000 AU
#  e      =   0.723725
#  i      =  44.055091 deg
#  peri   = 253.996655 deg
#  node   =  16.828150 deg
#  Pi     = 270.824805 deg
#  q      =   0.696490 AU
#  f      = 285.999629 deg
#  M      = 349.356828 deg
#  Q      =   4.345511 AU
#  n      =   0.246232 deg/day
#  T      =   4.002764 years
#  Last perihelion JD = 2457161.884484 (2015-05-19 09:13:39.383003)
#  Tj     =   2.754720


   dur = json_data['best_conv_inter']
   lengths = []
   times = []
   for key in dur:
      if "obs" in key:
         print(key, dur[key]['time_data'][-1])
         print(key, dur[key]['length'][-1])
         lengths.append(dur[key]['length'][-1])
         times.append(dur[key]['time_data'][-1])
   max_time = np.max(times)
   max_len = np.max(lengths)
      #for ckey in json_data[key]:
      #   print("     ", json_data[key][ckey])

   d.text((12,160), "Duration :" , font=fnt, fill=(0,0,0))
   d.text((130,160), "{:s}".format(str(max_time)[0:6]), font=fnt, fill=(0,0,0))

   d.text((12,180), "Track Length:" , font=fnt, fill=(0,0,0))
   d.text((130,180), "{:s}".format(str(max_len)[0:8]), font=fnt, fill=(0,0,0))
   rad_ra, rad_dec = json_data['radiant_eq']
   rad_ra = math.degrees(rad_ra)
   rad_dec = math.degrees(rad_dec)
   radiant_info = str(rad_ra)[0:6] + " / " + str(rad_dec)[0:6]
   d.text((12,200), "Radiant:         " , font=fnt, fill=(0,0,0))
   d.text((130,200), radiant_info, font=fnt, fill=(0,0,0))

   d.text((12,220), "Peak Magnitude: " , font=fnt, fill=(0,0,0))
   d.text((130,220), "TBD", font=fnt, fill=(0,0,0))
   d.text((12,240), "Shower:         " , font=fnt, fill=(0,0,0))
   d.text((130,240), "TBD", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head.jpg"
   head1.save(head_file)
   head1.close()

   head2 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head2)
   d.text((10,10), "Observations", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head2.jpg"
   head2.save(head_file)
   head2.close()

   head3 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head3)
   d.text((10,10), "Atmospheric Trajectory", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head3.jpg"
   head3.save(head_file)
   head3.close()

   head4 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head4)
   d.text((10,10), "Orbit", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head4.jpg"
   head4.save(head_file)
   head4.close()

   head5 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head5)
   d.text((10,10), "Velocity", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head5.jpg"
   head5.save(head_file)
   head5.close()

   head6 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head6)
   d.text((10,10), "Lag", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head6.jpg"
   head6.save(head_file)
   head6.close()

   head7 = Image.new('RGB', (600,50), color=(255,255,255))
   fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 25)
   d = ImageDraw.Draw(head7)
   d.text((10,10), "Residuals", font=fnt, fill=(0,0,0))
   head_file = job_dir + "mike_head7.jpg"
   head7.save(head_file)
   head7.close()



   
   plots = {}
   plots['observations'] = []
   plots['res_error'] = []
   plots['ground_track'] = []
   plots['orbit'] = []
   plots['lag'] = []
   plots['velocity'] = []
   files = glob.glob(job_dir + "thumbs/*.png")
   for file in files:
      if "OBS" in file and "caption" not in file:
         plots['observations'].append(file)
      if "residuals" in file:
         plots['res_error'].append(file)
      if "ground_track" in file:
         plots['ground_track'].append(file)
      if "orbit" in file:
         plots['orbit'].append(file)
      if "lag" in file:
         plots['lag'].append(file)
      if "velocities" in file or "lengths" in file:
         plots['velocity'].append(file)


   oc = 1
   for file in plots['observations']:
      if "OBS" in file and "caption" not in file:
         caption = "blah"
         el = file.split("-")
         last = el[-2] + "-" + el[-1]
         title = last.replace(".png", "")
         if el[-2] in station_data:
            station_name = el[-2]
            caption = station_data[station_name]['opr_name'] + " - " + station_data[station_name]['obs_name'] 
            caption2 = station_data[station_name]['lat'] + "$^\circ$N " + station_data[station_name]['lon'] + "$^\circ$" + "W "  + station_data[station_name]['alt'] + "m"
            hcaption2 = title + " : " + station_data[station_name]['lat'] + "&deg;N " + station_data[station_name]['lon'] + "&deg;" + "W "  + station_data[station_name]['alt'] + "m"
            json_data['as6_info'][title] = caption + "<BR>" + hcaption2
         caption_image(file, title, caption, caption2, "")
         oc = oc + 1
   
   cmd = "montage " + thumb_dir + "*OBS*caption*.png -geometry +2+0 " + job_dir + "mike-obs.png"
   os.system(cmd) 

   cmd = "montage " + thumb_dir + "*RED*.png -geometry +2+0 " + job_dir + "mike-red.png"
   print(cmd)
   os.system(cmd) 
   
   cmd = "montage " + thumb_dir + "*residuals*.png -geometry +2+0 " + job_dir + "mike-rez.png"
   os.system(cmd) 
   
   cmd = "montage " + thumb_dir + "*lag*.png -geometry +2+0 " + job_dir + "mike-lg.png"
   os.system(cmd) 
   
   cmd = "montage " + thumb_dir + "*velocities*.png "  + thumb_dir + "*lengths*.png -geometry +2+2 " + job_dir + "mike-vel.png"
   os.system(cmd) 
   
   cmd = "montage " + thumb_dir + "*orbit*.png -geometry +2+0 " + job_dir + "mike-orb.png"
   os.system(cmd) 

   cmd = "montage " + thumb_dir + "*ground*.png -geometry +2+0 " + job_dir + "mike-gnd.png"
   os.system(cmd) 
   
   file_list = job_dir + "mike_head.jpg " + job_dir + "mike_head2.jpg " + job_dir + "mike-obs.png "  + \
      job_dir + "mike-red.png " + \
      job_dir + "mike_head3.jpg "  + job_dir + "mike-gnd.png " + \
      job_dir + "mike_head4.jpg " + job_dir + "mike-orb.png " + \
      job_dir + "mike_head5.jpg " + job_dir + "mike-vel.png " + \
      job_dir + "mike_head6.jpg " + job_dir + "mike-lg.png " + \
      job_dir + "mike_head7.jpg " + job_dir + "mike-rez.png"
   cmd = "convert -append " + file_list + " " + job_dir + job_file + "-all.jpg"
   print(cmd)
   os.system(cmd)

   json_data['as6_info']['start_point'] = "{:s}{:s}N {:s}{:s}W {:s} km ".format(str(math.degrees(json_data['rbeg_lat']))[0:6], deg, str(math.degrees(json_data['rbeg_lon']))[0:6], deg, str(json_data['rbeg_ele']/1000)[0:5])
   json_data['as6_info']['end_point'] = "{:s}{:s}N {:s}{:s}W {:s} km ".format(str(math.degrees(json_data['rend_lat']))[0:6], deg, str(math.degrees(json_data['rend_lon']))[0:6], deg, str(json_data['rend_ele']/1000)[0:5])
   json_data['as6_info']['velocity'] = "{:s} KM/Second".format(str(json_data['v_init']/1000)[0:6])
   json_data['as6_info']['duration'] = "{:s}".format(str(max_time)[0:6])
   json_data['as6_info']['track_length'] = "{:s}".format(str(max_len)[0:8])
   json_data['as6_info']['radiant'] = radiant_info 
   json_data['as6_info']['peak_magnitude'] = "TBD"
   json_data['as6_info']['shower'] = "TBD"
  
   save_json_file(json_file, json_data) 
