"""
run the DFM many times changing a bit each time 
"""

import os

# decide var(s) you want to change
# make many config files
# run the DFM many times 1x per config

dfm_cfg_dir = "/home/ams/amscams/pipeline/DFM/AUTO_TESTS/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_original/"
dfn_bin_dir = "/home/ams/DFN_darkflight/DFN_darkflight_mike/"

base_cfg_file = dfm_cfg_dir + "DFN_DFM_TEST_G1_MURRIL_MIKE.cfg"
wind_file = base_cfg_file.replace("_MIKE.cfg", "_wind.csv")
cfg_fn = base_cfg_file.split("/")[-1]
proj_name = cfg_fn.replace(".cfg", "")
temp_dir = dfm_cfg_dir + "RESULTS/"
var_to_change = 'z0' 
var_to_change = 'exposure_time' 
# time do in 2 hour increments 
alt_values = ['25000', '22500', '20000', '17500', '15000', '12500', '10000', '7500', '5000', '2500']
var_values = [
        '2015-11-27T00:43:51.626',
        '2015-11-27T01:43:51.626',
        '2015-11-27T02:43:51.626',
        '2015-11-27T03:43:51.626',
        '2015-11-27T04:43:51.626',
        '2015-11-27T05:43:51.626',
        '2015-11-27T06:43:51.626',
        '2015-11-27T07:43:51.626',
        '2015-11-27T08:43:51.626',
        '2015-11-27T09:43:51.626',
        '2015-11-27T10:43:51.626',
        '2015-11-27T11:43:51.626',
        '2015-11-27T12:43:51.626',
        '2015-11-27T13:43:51.626',
        '2015-11-27T14:43:51.626',
        '2015-11-27T15:43:51.626',
        '2015-11-27T16:43:51.626',
        '2015-11-27T17:43:51.626',
        '2015-11-27T18:43:51.626',
        '2015-11-27T19:43:51.626',
        '2015-11-27T20:43:51.626',
        '2015-11-27T21:43:51.626',
        '2015-11-27T22:43:51.626',
        '2015-11-27T23:43:51.626'
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
