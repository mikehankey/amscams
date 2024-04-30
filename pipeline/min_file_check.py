import datetime
import os
# loop over each HD file parse the date, hour, minute and camera number and populate a minute dict 
# with the files found . use this to see when/where we are missing minutes of coverage which equates to camera down time

check_dir = "/mnt/ams2/HD/"

# first make the minute dict
# starting from the current minute, go back 24 hours
# and print out the date and time to the minute for every minute in the last 24 hours
# these will be the keys for the minute dict which we will populate as we go
minute_dict = {}
current_time = datetime.datetime.now()
for i in range(0, 2880):
    minute = current_time - datetime.timedelta(minutes=i)
    min_key = minute.strftime('%Y_%m_%d_%H_%M')
    minute_dict[min_key] = []
files = os.listdir(check_dir)
for file in files:
    if ".mp4" not in file:
        continue
    if "trim" in file:
        continue
    if "crop" in file:
        continue
    file_parts = file.split("_")
    year, month, day, hour, min, sec, msec, cam_num = file_parts[0], file_parts[1], file_parts[2], file_parts[3], file_parts[4], file_parts[5], file_parts[6], file_parts[7]
    min_key = f"{year}_{month}_{day}_{hour}_{min}"
    if min_key in minute_dict:
        minute_dict[min_key].append([cam_num, sec])
missing = 0
good = 0
for key in sorted(minute_dict):
    if len(minute_dict[key]) == 0:
        print(key, "MISSING")
        missing += 1
    else:
        print(key, len(minute_dict[key]))
        good += 1
print("Missing minutes:", missing)
print("Good minutes:", good)
perc = good / (good + missing) * 100
print("Percent good:", perc)