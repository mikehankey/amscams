"""
run the DFM many times changing a bit each time 
"""

import os

# decide var(s) you want to change
# make many config files
# run the DFM many times 1x per config

dfm_cfg_dir = "/home/ams/amscams/pipeline/DFM/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_original/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_mike2/"
#base_cfg_file = dfm_cfg_dir + "2024_01_21_DE/2024_01_21_DE.cfg"
base_cfg_file = dfm_cfg_dir + "2023_12_29_AZ/2023_12_29_AZ.cfg"
wind_file = base_cfg_file.replace(".cfg", "_wind.csv")
cfg_fn = base_cfg_file.split("/")[-1]
proj_name = cfg_fn.replace(".cfg", "")
temp_dir = dfm_cfg_dir + "temp/"
var_to_change = 'z0' 
var_to_change = 'exposure_time' 
# time do in 2 hour increments 
alt_values = ['25000', '22500', '20000', '17500', '15000', '12500', '10000', '7500', '5000', '2500']
var_values = [
        '2023-12-29T00:40:32.800',
        '2023-12-29T01:40:32.800',
        '2023-12-29T02:40:32.800',
        '2023-12-29T03:40:32.800',
        '2023-12-29T04:40:32.800',
        '2023-12-29T05:40:32.800',
        '2023-12-29T06:40:32.800',
        '2023-12-29T07:40:32.800',
        '2023-12-29T08:40:32.800',
        '2023-12-29T09:40:32.800',
        '2023-12-29T10:40:32.800',
        '2023-12-29T11:40:32.800',
        '2023-12-29T12:40:32.800',
        '2023-12-29T13:40:32.800',
        '2023-12-29T14:40:32.800',
        '2023-12-29T15:40:32.800',
        '2023-12-29T16:40:32.800',
        '2023-12-29T17:40:32.800',
        '2023-12-29T18:40:32.800',
        '2023-12-29T19:40:32.800',
        '2023-12-29T20:40:32.800',
        '2023-12-29T21:40:32.800',
        '2023-12-29T22:40:32.800',
        '2023-12-29T23:40:32.800'
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
