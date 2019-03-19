#!/usr/bin/python3

from sympy import Point3D, Line3D, Segment3D, Plane
import sys
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from lib.UtilLib import convert_filename_to_date_cam
from lib.FileIO import cfe


from mpl_toolkits import mplot3d
import math
from lib.FileIO import load_json_file, save_json_file

def plot_meteor_obs(meteor, meteor_file):
   fig_file = meteor_file.replace(".json", "-fig2.png")
   fig = plt.figure()
   ax = Axes3D(fig)
   x = [meteor['obs1']['ObsX'], meteor['obs2']['ObsX']]
   y = [meteor['obs1']['ObsY'], meteor['obs2']['ObsY']]
   z = [meteor['obs1']['ObsZ'], meteor['obs2']['ObsZ']]
   ax.scatter3D(x,y,z,c='r',marker='o')
 
   meteor_points1 = meteor['meteor_points1']
   meteor_points2 = meteor['meteor_points2']
   for mx,my,mz in meteor_points1:
      ax.plot([meteor['obs1']['ObsX'],mx],[meteor['obs1']['ObsY'],my],[meteor['obs1']['ObsZ'],mz],c='g')
   for mx,my,mz in meteor_points1:
      ax.plot([meteor['obs2']['ObsX'],mx],[meteor['obs2']['ObsY'],my],[meteor['obs2']['ObsZ'],mz],c='g')

   plt.savefig(fig_file)

def plot_meteor(meteor, meteor_file):
   fig_file = meteor_file.replace(".json", "-fig1.png")
   fig = plt.figure()
   ax = Axes3D(fig)
   #print(meteor)

   # plot observers
   #ax.scatter3D(x,y,z,c='r',marker='o')

   meteor_points1 = meteor['meteor_points1']
   meteor_points2 = meteor['meteor_points2']

   xs = []
   ys = []
   zs = []
   for mx,my,mz in meteor_points1:
      if mz > 10:
         xs.append(mx)
         ys.append(my)
         zs.append(mz)
   ax.scatter3D(xs,ys,zs,marker='x')

   for mx,my,mz in meteor_points2:
      if mz > 10:
         xs.append(mx)
         ys.append(my)
         zs.append(mz)
   ax.scatter3D(xs,ys,zs,marker='o')

   plt.show()
   plt.savefig(fig_file)


def compute_solution(meteor):
   # vector factor
   vfact = 180 

   # plot line vectors for obs1
   Obs1X = meteor['obs1']['ObsX']
   Obs1Y = meteor['obs1']['ObsY']
   Obs1Z = meteor['obs1']['ObsZ']
   mv = meteor['obs1']['vectors']
   vp1 = []
   for data in mv:
      vx,vy,vz = data
      veX = Obs1X + ( vx * vfact)
      veY = Obs1Y + ( vy * vfact)
      veZ = Obs1Z + ( vz * vfact)
      vp1.append((veX,veY,veZ))
   plane1 = Plane(Point3D(Obs1X,Obs1Y,Obs1Z),Point3D(vp1[0][0],vp1[0][1],vp1[0][2]),Point3D(vp1[-1][0], vp1[-1][1], vp1[-1][2]))

   # plot line vectors for obs2
   Obs2X = meteor['obs2']['ObsX']
   Obs2Y = meteor['obs2']['ObsY']
   Obs2Z = meteor['obs2']['ObsZ']
   mv = meteor['obs2']['vectors']
   vp2 = []
   for data in mv:
      vx,vy,vz = data
      veX = Obs2X + ( vx * vfact)
      veY = Obs2Y + ( vy * vfact)
      veZ = Obs2Z + ( vz * vfact)
      vp2.append((veX,veY,veZ))

 # plot line vectors for obs2
   Obs2X = meteor['obs2']['ObsX']
   Obs2Y = meteor['obs2']['ObsY']
   Obs2Z = meteor['obs2']['ObsZ']
   mv = meteor['obs2']['vectors']
   vp2 = []
   for data in mv:
      vx,vy,vz = data
      veX = Obs2X + ( vx * vfact)
      veY = Obs2Y + ( vy * vfact)
      veZ = Obs2Z + ( vz * vfact)
      vp2.append((veX,veY,veZ))

   plane2 = Plane(Point3D(Obs2X,Obs2Y,Obs2Z),Point3D(vp2[0][0],vp2[0][1],vp2[0][2]),Point3D(vp2[-1][0], vp2[-1][1], vp2[-1][2]))

   meteor_points1 = []
   meteor_points2 = []

   for veX,veY,veZ in vp1:
      line = Line3D(Point3D(Obs1X,Obs1Y,Obs1Z),Point3D(veX,veY,veZ))

      inter = plane2.intersection(line)
      mx = float((eval(str(inter[0].x))))
      my = float((eval(str(inter[0].y))))
      mz = float((eval(str(inter[0].z))))
      meteor_points1.append((mx,my,mz))

   for veX,veY,veZ in vp2:
      line = Line3D(Point3D(Obs2X,Obs2Y,Obs2Z),Point3D(veX,veY,veZ))

      inter = plane1.intersection(line)
      mx = float((eval(str(inter[0].x))))
      my = float((eval(str(inter[0].y))))
      mz = float((eval(str(inter[0].z))))
      meteor_points2.append((mx,my,mz))

   xs = []
   ys = []
   zs = []
   for mx,my,mz in meteor_points1:
      xs.append(mx)
      ys.append(my)
      zs.append(mz)

   for mx,my,mz in meteor_points2:
      xs.append(mx)
      ys.append(my)
      zs.append(mz)

   meteor['meteor_points1'] = meteor_points1
   meteor['meteor_points2'] = meteor_points2
   meteor['vp1'] = vp1 
   meteor['vp2'] = vp2 
   return(meteor)





def plot_xyz(x,y,z,meteor):
   vfact = 180 
   fig = plt.figure()
   ax = Axes3D(fig)
   #line1, line2 = make_lines_for_obs(cart1)
   #x = [line1[0][0],line1[0][1],line2[0][1]]
   #y = [line1[1][0],line1[1][1],line2[1][1]]
   #z = [line1[2][0],line1[2][1],line2[2][1]]


   ax.scatter3D(x,y,z,c='r',marker='o')


   # plot line vectors for obs1 
   Obs1X = meteor['obs1']['ObsX']
   Obs1Y = meteor['obs1']['ObsY']
   Obs1Z = meteor['obs1']['ObsZ']
   mv = meteor['obs1']['vectors']
   vp = []
   for data in mv:
      vx,vy,vz = data
      veX = Obs1X + ( vx * vfact)
      veY = Obs1Y + ( vy * vfact)
      veZ = Obs1Z + ( vz * vfact)
      #ax.plot([Obs1X,veX],[Obs1Y,veY],[Obs1Z,veZ], color='green')
      vp.append((veX,veY,veZ))


   plane1 = Plane(Point3D(Obs1X,Obs1Y,Obs1Z),Point3D(vp[0][0],vp[0][1],vp[0][2]),Point3D(vp[-1][0], vp[-1][1], vp[-1][2]))

   # plot line vectors for obs2
   Obs2X = meteor['obs2']['ObsX']
   Obs2Y = meteor['obs2']['ObsY']
   Obs2Z = meteor['obs2']['ObsZ']
   mv = meteor['obs2']['vectors']
   vp2 = []
   for data in mv:
      vx,vy,vz = data
      veX = Obs2X + ( vx * vfact)
      veY = Obs2Y + ( vy * vfact)
      veZ = Obs2Z + ( vz * vfact)
      vp2.append((veX,veY,veZ))

   plane2 = Plane(Point3D(Obs2X,Obs2Y,Obs2Z),Point3D(vp2[0][0],vp2[0][1],vp2[0][2]),Point3D(vp2[-1][0], vp2[-1][1], vp2[-1][2]))

   meteor_points1 = []
   meteor_points2 = []

   for veX,veY,veZ in vp:
      line = Line3D(Point3D(Obs1X,Obs1Y,Obs1Z),Point3D(veX,veY,veZ))

      inter = plane2.intersection(line)
      mx = float((eval(str(inter[0].x))))
      my = float((eval(str(inter[0].y))))
      mz = float((eval(str(inter[0].z))))
      #ax.scatter3D(mx,my,mz,c='r',marker='x')
      ax.plot([Obs1X,mx],[Obs1Y,my],[Obs1Z,mz],c='g')
      meteor_points1.append((mx,my,mz))


   for veX,veY,veZ in vp2:
      line = Line3D(Point3D(Obs2X,Obs2Y,Obs2Z),Point3D(veX,veY,veZ))

      inter = plane1.intersection(line)
      mx = float((eval(str(inter[0].x))))
      my = float((eval(str(inter[0].y))))
      mz = float((eval(str(inter[0].z))))
      #ax.scatter3D(mx,my,mz,c='r',marker='x')
      ax.plot([Obs2X,mx],[Obs2Y,my],[Obs2Z,mz],c='b')
      meteor_points2.append((mx,my,mz))

   xs = []
   ys = []
   zs = []
   for mx,my,mz in meteor_points1:
      xs.append(mx)
      ys.append(my)
      zs.append(mz)
   ax.scatter3D(xs,ys,zs,marker='x')

   for mx,my,mz in meteor_points2:
      xs.append(mx)
      ys.append(my)
      zs.append(mz)
   ax.scatter3D(xs,ys,zs,marker='o')


   #ax.set_zlim(0, 140)
   #ax.set_xlim(np.min(x)-100, np.max(x)+100)
   #ax.set_ylim(np.min(y)-100, np.max(y)+100)

   ax.set_xlabel('X Label')
   ax.set_ylabel('Y Label')
   ax.set_zlabel('Z Label')
   plt.show()

def make_obs_vectors(mo):
   fc = 0
   mo_vectors = []
   for data in mo['meteor_frame_data']:
      az = data[9]
      el = data[10]
      vx = math.sin(math.radians(az)) * math.cos(math.radians(el))
      vy = math.cos(math.radians(az)) * math.cos(math.radians(el))
      vz = math.sin(math.radians(el))
      mo_vectors.append((vx,vy,vz))
   return(mo_vectors)

def setup_obs(mo1,mo2):
   meteor = {}

   meteor['obs1'] = {}
   meteor['obs2'] = {}

   lat1 =  float(mo1['cal_params']['site_lat'])
   lon1 =  float(mo1['cal_params']['site_lng'])
   alt1 =  float(mo1['cal_params']['site_alt']) / 1000

   lat2 =  float(mo2['cal_params']['site_lat'])
   lon2 =  float(mo2['cal_params']['site_lng'])
   alt2 =  float(mo2['cal_params']['site_alt']) / 1000

   Obs1Z = alt1
   Obs1Y = 0 
   Obs1X = 0 

   Obs2Z = alt2 - alt1
   Obs2Y = (lat2 - lat1)*111.14
   Obs2X = (lon2 - lon1)*111.32*math.cos(((lat1+lat2)/2)*math.pi/180)

   meteor['obs1']['lat'] = lat1
   meteor['obs1']['lon'] = lon1
   meteor['obs1']['alt'] = alt1
   meteor['obs1']['ObsX'] = Obs1X
   meteor['obs1']['ObsY'] = Obs1Y
   meteor['obs1']['ObsZ'] = Obs1Z

   meteor['obs2']['lat'] = lat2
   meteor['obs2']['lon'] = lon2
   meteor['obs2']['alt'] = alt2
   meteor['obs2']['ObsX'] = Obs2X
   meteor['obs2']['ObsY'] = Obs2Y
   meteor['obs2']['ObsZ'] = Obs2Z

   mo1_vec =  make_obs_vectors(mo1)
   mo2_vec =  make_obs_vectors(mo2)

   meteor['obs1']['vectors'] = mo1_vec
   meteor['obs2']['vectors'] = mo2_vec

   x = [Obs1X,Obs2X]
   y = [Obs1Y,Obs2Y]
   z = [Obs1Z,Obs2Z]

   #print(meteor)
   plot_xyz(x,y,z,meteor)
   return(meteor)

obs1_file, obs2_file = sys.argv[1], sys.argv[2]

hd_datetime, cam1, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(obs1_file)
hd_datetime, cam2, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(obs2_file)
meteor_file = "/mnt/ams2/multi_station/" + hd_y + "_" + hd_m + "_" + hd_d + "/" + hd_y + "_" + hd_m + "_" + hd_d + hd_h + "_" + hd_M + "_" + hd_s + "_" + cam1 + "_" + cam2 + "-solved.json" 
print(meteor_file)
if cfe(meteor_file) == 0:
   mo1 = load_json_file(obs1_file)
   mo2 = load_json_file(obs2_file)
   meteor = setup_obs(mo1,mo2)
   meteor = compute_solution(meteor)
else:
   meteor = load_json_file(meteor_file)
  
#plot_meteor(meteor,meteor_file)
plot_meteor_obs(meteor, meteor_file)
save_json_file(meteor_file, meteor)


