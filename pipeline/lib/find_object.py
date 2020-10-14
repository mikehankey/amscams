
def find_hd(sd_trim_file, dur):
   PIPE_OUT = PIPELINE_DIR + "IN/"
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_trim_file)
   sdfn = sd_trim_file.split("/")[-1]
   sd_trim_num = get_trim_num(sd_trim_file)
   print("SD FILE TIME:", f_datetime)
   print("SD TRIM NUM:", sd_trim_num)
   extra_trim_sec = int(sd_trim_num) / 25
   print("EXTRA TRIM SECONDS:", sd_trim_num)
   sd_trim_start = f_datetime + datetime.timedelta(seconds=extra_trim_sec)
   sd_start_min_before = sd_trim_start + datetime.timedelta(seconds=-60)
   sd_start_min_after = sd_trim_start + datetime.timedelta(seconds=+60)

   # get the HD files within +/- 1 min of the SD trim start time for this cam
   print("SD TRIM START TIME:", sd_trim_start)
   date_wild = sd_trim_start.strftime("%Y_%m_%d_%H_%M")
   date_wild_before = sd_start_min_before.strftime("%Y_%m_%d_%H_%M")
   date_wild_after = sd_start_min_after.strftime("%Y_%m_%d_%H_%M")
   print("CAM:", cam)
   print("DATE WILD:", date_wild)
   hd_wild = "/mnt/ams2/HD/" + date_wild + "*" + cam + ".mp4"
   hd_wild_before = "/mnt/ams2/HD/" + date_wild_before + "*" + cam + ".mp4"
   hd_wild_after = "/mnt/ams2/HD/" + date_wild_after + "*" + cam + ".mp4"
   print("HD WILD:", hd_wild)
   hd_matches = glob.glob(hd_wild)

   best_hd_matches = []

   for hd_file in hd_matches:
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
      hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()

      print("SD/HD TIME DIFF:", hd_time_diff)
      if -60 <= hd_time_diff <= 0:
         best_hd_matches.append((hd_file, hd_time_diff))
      if hd_time_diff > 0:
         hd_matches_before = glob.glob(hd_wild_before)

         for hd_file in hd_matches_before:
            (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
            hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()
            print("BEFORE SD/HD TIME DIFF:", hd_time_diff)
            if -60 <= hd_time_diff <= 0:
               best_hd_matches.append((hd_file,hd_time_diff))

   print("BEST HD FILE:", best_hd_matches)
   if len(best_hd_matches) == 1:
      hd_file = best_hd_matches[0][0]
      hd_time_diff = best_hd_matches[0][1]
      hd_trim_start = abs(hd_time_diff) * 25
      hd_trim_end = hd_trim_start + dur
      hd_trim_out = PIPE_OUT + sdfn
      hd_trim_out = hd_trim_out.replace("-SD", "-HD")
      print("HD TRIM OUT:", hd_trim_out)
      if cfe(hd_trim_out) == 0:
         hd_trim_start, hd_trim_end, status = buffer_start_end(hd_trim_start, hd_trim_end, 10, 1499)
         trim_min_file(hd_file, hd_trim_out, hd_trim_start, hd_trim_end)
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)

   # We should only need the after file if the current file worked but the hd time is at the EOF

   return(hd_trim_out)
