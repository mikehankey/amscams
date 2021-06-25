import json
import datetime

def meteor_scan_api_controller(in_data):
   if "cmd" in in_data:
      cmd = in_data['cmd']
   else:
      cmd = None
   if "in_date" in in_data:
      in_date = in_data['in_date']
   else:
      in_date = datetime.datetime.now().strftime("%Y_%m_%d")
   if "page_num" in in_data:
      page_num = in_data['page_num']
   else:
      page_num = 1
   if "per_page" in in_data:
      per_page = in_data['per_page']
   else:
      per_page = 500
   data = {}
   data['msg'] = "ok"

   from Classes.MeteorNew import Meteor 

   MM = Meteor()
   if cmd == "update_roi_crop":
      if "sd_video_file" in in_data:
         sd_video_file = in_data['sd_video_file']
      if "roi_crop" in in_data:
         resp = MM.update_roi_crop(sd_video_file, in_data['roi_crop'])
      else:
         resp = {}
         resp['msg'] = "err"
      return(json.dumps(resp))


   if cmd == "get_meteors":
      html,rows,stats = MM.scan_report(in_date,page_num,per_page)
      data['html'] = html
      data['row_data'] = rows
      data['stats'] = stats
      data = json.dumps(data)
   if cmd == "confirm_meteor":
      MM.human_confirm_meteor(in_data['sd_video_file'])

   if cmd == "save_human_data":
      station_id = in_data['station_id']
      sd_video_file = in_data['sd_video_file']
      human_data = in_data['human_data']
      MM.save_human_data(station_id, sd_video_file, human_data)
   if cmd == "del_meteor_obs":
      if "sd_video_file" in in_data and "reclass" in in_data:
         sd_video_file = in_data['sd_video_file']
         reclass = in_data['reclass']
         MM.delete_local_meteor(sd_video_file, reclass)
         print("LOCAL METEOR DELETED!")
   return(data)
