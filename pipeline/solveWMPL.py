#!/usr/bin/python3

import matplotlib
matplotlib.use('agg')

from lib.PipeUtil import load_json_file, save_json_file, cfe, calc_dist
import sys
import numpy as np
import datetime
import math

# Import modules from WMPL
import wmpl.Utils.TrajConversions as trajconv
import wmpl.Utils.SolarLongitude as sollon
from wmpl.Trajectory import Trajectory as traj

import time
from wmpl.Utils.TrajConversions import equatorialCoordPrecession_vect, J2000_JD

def get_best_obs(obs):
   best_dist = 99999
   best_file = None
   for file in obs:
      if best_file is None:
         best_file = file

      mid_x = np.mean(obs[file]['xs'])
      mid_y = np.mean(obs[file]['ys'])
      dist_to_center = calc_dist((mid_x,mid_y), (1920/2, 1080/2))
      if dist_to_center < best_dist:
         best_file = file
         best_dist = dist_to_center


   print("BEST:", best_file)
   return(best_file)


def WMPL_solve(obs):
    solve_dir = "/mnt/ams2/EVENTS/"
    # Inputs are RA/Dec
    meastype = 2

    # Reference julian date
    start_times = []
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
           file = get_best_obs(obs[station_id])
        else:
           for bfile in obs[station_id]:
               file = bfile


        if len(obs[station_id][file]['times']) > 0:
           start_times.append(obs[station_id][file]['times'][0])   

    event_start = sorted(start_times)[0]
     
    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
    solve_dir += day + "/" + e_dir 

    event_start_dt = datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f")
    jd_ref = trajconv.datetime2JD(event_start_dt)
    print(event_start_dt, jd_ref)


    # Init new trajectory solving
    traj_solve = traj.Trajectory(jd_ref, output_dir=solve_dir, meastype=meastype, save_results=True, monte_carlo=False, show_plots=False)
   
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
            file = get_best_obs(obs[station_id])
        else:
            for bfile in obs[station_id]:
                file = bfile
         
        if True:
            lat,lon,alt = obs[station_id][file]['loc']
            lat,lon,alt = float(lat), float(lon), float(alt)
            azs = np.radians(obs[station_id][file]['azs'])
            els = np.radians(obs[station_id][file]['els'])
            print("ELS:", els)
            if len(azs) == 0:
                continue
            times = []
            for i in range(0,len(azs)):
                times.append(i/25)
        
            # Set input points for the first site
            print(station_id)
            print(azs)
            print(els)
            print(times)
            traj_solve.infillTrajectory(azs, els, times, np.radians(float(lat)), np.radians(float(lon)), alt, station_id=station_id)

    traj_solve.run()

    mj['wmpl'] = e_dir
    save_json_file(meteor_file, mj)
    print("Saved:", meteor_file) 


cmd = sys.argv[1]
meteor_file = sys.argv[2]

if cmd == "solve":
   mj = load_json_file(meteor_file)
   obs = mj['multi_station_event']['obs']
   WMPL_solve(obs)
if cmd == "report":
   WMPL_report(meteor_file)
