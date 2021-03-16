from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs

class Camera:
   def __init__(self, cam_num=None, cams_id=None, json_conf=None):
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")
      if cam_num is not None:
         for cam in json_conf['cameras']:
            if str(cam) == "cam" + str(cam_num):
               cam_info = json_conf['cameras'][cam]
               cam_info['cam_num'] = cam
               print(cam_info)
      if cams_id is not None:
         for cam in json_conf['cameras']:
            tcams_id = json_conf['cameras'][cam]
            if str(tcams_id) == str(cams_id):
               cam_info = json_conf['cameras'][cam]
               cam_info['cam_num'] = cam.replace("cam", "")
               print(cam_info)
      self.cam_num = cam_info['cam_num']
      self.cams_id = cam_info['cams_id']
      self.ip = cam_info['ip']
      self.sd_url = cam_info['sd_url']
      self.hd_url = cam_info['hd_url']

if __name__ == "__main__":
   import sys
   camera = Camera(cam_num=1)

