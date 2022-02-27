#!/usr/bin/python3
# convert wind sounding profile DFN to profile format
# https://rucsoundings.noaa.gov/get_raobs.cgi?data_source=RAOB&start_year=2022&start_month_name=Jan&start_mday=20&start_hour=12&start_min=0&n_hrs=1.0&fcst_len=shortest&airport=KDVN&text=Ascii%20text%20%28GSL%20format%29&hydrometeors=false&startSecs=1642680000&endSecs=1642683600
# https://rucsoundings.noaa.gov/raob_format.html
# IN
#          Prs         Hgt    Tmp    DPT   WDir     Wspd HHMM bearing range
# OUT
# height,tempk,press,rhum,wind,wdir
#RH≈100−5(T−TD)

in_file = "wind_data.txt"
out_file = in_file.replace(".txt","-DFN.csv")

fp = open(in_file)
print("height,tempk,pressure,rh,wind_speed,wind_dir")
last_temp_c_10 = None 
last_temp_dp_c_10 = None 
last_wind_dir = None
last_wind_speed = None
for line in fp:
   line = line.replace("\n", "")
   data = line.split()
   if len(data) < 1:
      continue
   if data[0] == "4" or data[0] == "5" or data[0] == "6":
      pressure = data[1]
      height = data[2]
      temp_c_10 = int(data[3]) * .1
      temp_dp_c_10 = int(data[4]) * .1 
      if temp_c_10 > 9000:
         if last_temp_c_10 is not None:
            temp_c_10 = last_temp_c_10 
            temp_dp_c_10 = last_temp_dp_c_10 
         else:
            continue


      wind_dir = float(data[5])
      wind_speed = float(data[6])
      if wind_dir > 9000:
         if last_wind_dir is not None:
            wind_dir = last_wind_dir
            wind_speed = last_wind_speed

      rtime = data[7]
      bearing = data[8]
      range = data[9]
 
      rh_dt = temp_c_10 - temp_dp_c_10
      #print("RH DT:", rh_dt)
      rh_dt5 = rh_dt * 5
      #print("RH DT*5:", rh_dt5)
      rh = 100 - rh_dt5
      #print("RH:", rh)
 

      rh = round(100 - 5 * (temp_c_10 - temp_dp_c_10),2)
      if rh < 0:
         rh = 0
      tempk = round(temp_c_10 + 273.15, 2)
      tempc = round(temp_c_10,2)
      temp_dp_c = round(temp_dp_c_10,2)
      #MS/S
      wind_speed_ms = round(wind_speed * .514444,2)
      # KNOTS?
      #wind_speed = round(wind_speed)
      line = "{:.2f},{:.2f},{:.2f},{:.2f},{:.2f},{:.2f}".format(float(height),float(tempk),float(pressure),float(rh),float(wind_speed_ms),float(wind_dir))
      print(line)
      last_temp_c_10 = temp_c_10 
      last_temp_dp_c_10 = temp_dp_c_10 
      last_wind_dir = wind_dir
      last_wind_speed = wind_speed
      

