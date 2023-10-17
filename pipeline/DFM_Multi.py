"""
run the DFM many times changing a bit each time 
"""

import os

# decide var(s) you want to change
# make many config files
# run the DFM many times 1x per config

dfm_cfg_dir = "/home/ams/amscams/pipeline/DFM/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_original/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_mike/"
base_cfg_file = dfm_cfg_dir + "2023_10_07_ID/2023_10_07_ID.cfg"
wind_file = base_cfg_file.replace(".cfg", "_wind.csv")
cfg_fn = base_cfg_file.split("/")[-1]
proj_name = cfg_fn.replace(".cfg", "")
temp_dir = dfm_cfg_dir + "temp/"
var_to_change = 'z0' 
var_to_change = 'exposure_time' 
# time do in 2 hour increments 
alt_values = ['25000', '22500', '20000', '17500', '15000', '12500', '10000', '7500', '5000', '2500']
var_values = [
        '2023-10-07T00:03:48.800',
        '2023-10-07T01:03:48.800',
        '2023-10-07T02:03:48.800',
        '2023-10-07T03:03:48.800',
        '2023-10-07T04:03:48.800',
        '2023-10-07T05:03:48.800',
        '2023-10-07T06:03:48.800',
        '2023-10-07T07:03:48.800',
        '2023-10-07T08:03:48.800',
        '2023-10-07T09:03:48.800',
        '2023-10-07T10:03:48.800',
        '2023-10-07T11:03:48.800',
        '2023-10-07T12:03:48.800',
        '2023-10-07T13:03:48.800',
        '2023-10-07T14:03:48.800',
        '2023-10-07T15:03:48.800',
        '2023-10-07T16:03:48.800',
        '2023-10-07T17:03:48.800',
        '2023-10-07T18:03:48.800',
        '2023-10-07T19:03:48.800',
        '2023-10-07T20:03:48.800',
        '2023-10-07T21:03:48.800',
        '2023-10-07T22:03:48.800',
        '2023-10-07T23:03:48.800'
        ]

cc = 0
for val in var_values:
   fp = open(base_cfg_file)
   new_conf = ""
   for line in fp:
      line = line.replace("\n", "")
      line = line.replace(" ", "")
      if "=" in line:
         vals = line.split("=")
         if len(vals) == 2:
            var, exval = vals
         else:
            var = "junk"
         if var == var_to_change:
            line = var + "=" + val 
      new_conf += line + "\n"
   fp.close()
   cfg = cfg_fn.replace(".cfg", str(cc) + ".cfg")
   temp_cfg_file = temp_dir + cfg
   out = open(temp_cfg_file, "w")
   out.write(new_conf)
   out.close()
   run_cmd = "/usr/bin/python3 {:s}DFN_DarkFlight.py -e {:s}  -w {:s} -K {:s} &".format(dfn_bin_dir, temp_cfg_file, wind_file, proj_name)
   print("RUN:", run_cmd)
   os.system(run_cmd)
   #exit()


   cc += 1
