import base64
import os
from flask import Flask, request, Response, make_response
from FlaskLib.Learning import learning_meteors_dataset
from FlaskLib.FlaskUtils import get_template
from FlaskLib.api_funcs import update_meteor_points, show_cat_stars, delete_meteor, restore_meteor, delete_meteors, reduce_meteor, delete_frame, crop_video
from FlaskLib.calib_funcs import calib_main, cal_file, show_masks, del_calfile, lens_model, edit_mask, edit_mask_points
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipePwdProtect import login_page, check_pwd_ajax
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page 
from FlaskLib.config_funcs import config_vars 
from FlaskLib.meteors_main import meteors_main , meteors_by_day, trash_page
from FlaskLib.super_stacks import stacks_main, stacks_day_hours, stacks_hour
from FlaskLib.min_detail import min_detail_main
from FlaskLib.live import live_view
from FlaskLib.TL import tl_menu 
from FlaskLib.man_reduce import meteor_man_reduce , save_man_reduce
from FlaskLib.man_detect import man_detect 
#from FlaskLib.Maps import make_map 

import json



app = Flask(__name__, static_url_path='/static')

#, ssl_context=('cert.pem', 'key.pem'))

# Main controller for AllSkyCams UI application.

@app.route('/TL/<amsid>/', methods=['GET', 'POST'])
def tlm(amsid):
   out = tl_menu(amsid)
   return(out)


@app.route('/maps/', methods=['GET', 'POST'])
def map_runner():

   points = request.args.get('points')
   lines = request.args.get('lines')


   img = make_map(points, lines)
   response = make_response(img.getvalue())
   response.headers['Content-Type'] = 'image/png'
   response.headers['Content-Disposition'] = 'filename=%d.png' % 0
   return response


@app.route('/event_detail/<event_id>/', methods=['GET', 'POST'])
def event_detail_control(event_id):
   from FlaskLib.Events import event_detail
   resp = event_detail(event_id)
   return(resp)

@app.route('/events/<date>/', methods=['GET', 'POST'])
def events_control(date):
   from FlaskLib.Events import list_events_for_day

   resp = list_events_for_day(date)
   return(resp)


@app.route('/', methods=['GET', 'POST'])
def main_menu():
   out = login_page()
   header = get_template("FlaskTemplates/header-login.html")
   footer = get_template("FlaskTemplates/footer-remote.html")
   out = out.replace("{HEADER}", header)
   out = out.replace("{FOOTER}", footer)
   return out

@app.route('/api/check_login', methods=['GET', 'POST'])
def chk_login():
   user = request.args.get('user')
   passwd = request.args.get('pwd')
   out = check_pwd_ajax(user, passwd)
   return out


@app.route('/api/delete_frame/<meteor_file>/', methods=['GET', 'POST'])
def del_frame(meteor_file):
   fn = request.args.get('fn')
   out = delete_frame(meteor_file,fn)
   return out

@app.route('/save_man_reduce/', methods=['GET', 'POST'])
def save_man_red():
   data = {}
   data['frame_data'] = request.form.get('frame_data')
   data['sd_video_file'] = request.form.get('sd_video_file')
   data['x'] = request.form.get('x')
   data['y'] = request.form.get('y')
   data['w'] = request.form.get('w')
   data['h'] = request.form.get('h')
   data['ow'] = request.form.get('ow')
   data['oh'] = request.form.get('oh')
   data['ScaleFactor'] = request.form.get('ScaleFactor')
   out = save_man_reduce(data)
   return(out)   

@app.route('/meteor_man_reduce/', methods=['GET', 'POST'])
def meteor_man_red():
  
   meteor_file = request.args.get('file')
   x = int(request.args.get('x'))
   y = int(request.args.get('y'))
   w = int(request.args.get('w'))
   h = int(request.args.get('h'))
   ScaleFactor = request.args.get('ScaleFactor')
   if ScaleFactor is None:
      ScaleFactor = 5
   else:
      ScaleFactor = int(ScaleFactor)
   step = request.args.get('step')
   if step is not None:
      step = int(step)   
   first_frame = request.args.get('first_frame')
   last_frame = request.args.get('last_frame')
   if first_frame is not None:
      first_frame = int(first_frame)
   if last_frame is not None:
      last_frame = int(last_frame)
   out = meteor_man_reduce(meteor_file, x,y,w,h,step,first_frame,last_frame,ScaleFactor)
   return out

@app.route('/man_detect/<min_file>/', methods=['GET', 'POST'])
def manual_detect(min_file):
  
   step = request.args.get('step')
   ff = request.args.get('ff')
   lf = request.args.get('lf')
   data = {}
   data['step'] = step
   data['ff'] = ff
   data['lf'] = lf
   out = man_detect(min_file, data)
   return(out)

@app.route('/api/reduce_meteor/<meteor_file>/', methods=['GET', 'POST'])
def red_meteor(meteor_file):
   out = reduce_meteor(meteor_file)
   return out

@app.route('/api/delete_meteor/<jsid>/', methods=['GET', 'POST'])
def del_meteor(jsid):
   data = {}
   data['data'] = request.args.get('data')
   out = delete_meteor(jsid, data)
   return out

@app.route('/api/restore_meteor/<jsid>/', methods=['GET', 'POST'])
def rest_meteor(jsid):
   data = {}
   data['data'] = request.args.get('data')
   out = restore_meteor(jsid, data)
   return out


@app.route('/api/delete_meteors/', methods=['GET', 'POST'])
def del_meteors():

   data = {}
   data['detections'] = request.form.get('detections')

   out = delete_meteors(data)
   return out

@app.route('/cal/lensmodel/<amsid>/', methods=['GET', 'POST'])
def lens_mod(amsid):
   out = lens_model(amsid)
   return out


@app.route('/cal/vars/<amsid>/', methods=['GET', 'POST'])
def op_vars(amsid):
   if request.method == "POST":
      data = request.form
   else:
      data = None
   out = config_vars(amsid,data)
   return out

@app.route('/cal/masks/<amsid>/', methods=['GET', 'POST'])
def masks(amsid):
   out = show_masks(amsid)
   return out

@app.route('/edit_mask/<amsid>/<camid>/', methods=['GET', 'POST'])
def emasks(amsid,camid):
   out = edit_mask(amsid,camid)
   return out


@app.route('/calfile/del/<amsid>/<calfile>/', methods=['GET', 'POST'])
def del_cfile(amsid, calfile):
   out = del_calfile(amsid, calfile)
   return out

@app.route('/calfile/<amsid>/<calfile>/', methods=['GET', 'POST'])
def cfile(amsid, calfile):
   out = cal_file(amsid, calfile)
   return out


@app.route('/calib/<amsid>/', methods=['GET', 'POST'])
def calib(amsid):
   req = {}
   req['cam_id_filter'] = request.args.get('cam_id_filter')
   out = calib_main(amsid,req)
   return out

@app.route('/live/<amsid>/', methods=['GET', 'POST'])
def live(amsid):
   out = live_view(amsid)
   return out

@app.route('/min_detail/<amsid>/<date>/<min_file>/', methods=['GET', 'POST'])
def min_detail(amsid, date, min_file):
   out = min_detail_main(amsid, date, min_file)
   return out


@app.route('/stacks_hour/<amsid>/<date>/<hour>/', methods=['GET', 'POST'])
def stacks_day_hour(amsid, date, hour):
   #req = {}
   #req['hour'] = request.args.get('hour')
   out = stacks_hour(amsid, date, hour)
   return out


@app.route('/stacks_day/<amsid>/<date>/', methods=['GET', 'POST'])
def stacks_day(amsid, date):
   req = {}
   req['hour'] = request.args.get('hour')
   out = stacks_day_hours(amsid, date, req)
   return out


@app.route('/stacks/<amsid>/', methods=['GET', 'POST'])
def stacks(amsid):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   hour = request.args.get('hour')

   req['start_day'] = start_day
   req['end_day'] = end_day 
   req['hour'] = hour
   req['days_per_page'] = request.args.get('days_per_page')
   req['p'] = request.args.get('p')

   out = stacks_main(amsid,req)
   return(out)




@app.route('/meteors_by_day/<amsid>/', methods=['GET', 'POST'])
def meteors_bd(amsid ):
   req = {}
   out = meteors_by_day(amsid,req)
   return(out)


# TRASH PAGE
@app.route('/trash/<amsid>/', methods=['GET', 'POST'])
def trash_pg(amsid ):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   req = {}
   req['start_day'] = start_day
   req['end_day'] = end_day
   out = trash_page(amsid, req)
   return(out)

# MAIN METEOR PAGE
@app.route('/meteors/<amsid>/', methods=['GET', 'POST'])
def meteors(amsid ):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   meteor_per_page = request.args.get('meteor_per_page')
   sort_by = request.args.get('sort_by')
   filter = request.args.get('filter')
   p = request.args.get('p')

   req['start_day'] = start_day
   req['end_day'] = end_day
   req['meteor_per_page'] = meteor_per_page
   req['p'] = p
   req['sort_by'] = sort_by 
   req['filter'] = filter
   out = meteors_main(amsid,req)

   return out

@app.route('/goto/meteor/<meteor_file>/', methods=['GET', 'POST'])
def goto_meteor(meteor_file):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   date = meteor_file[0:10] 
   out = detail_page(amsid, date, meteor_file )
   return out

@app.route('/meteors/<amsid>/<date>/<meteor_file>/', methods=['GET', 'POST'])
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out

@app.route('/LEARNING/METEORS/<amsid>', methods=['GET', 'POST'])
def lrn_meteors(amsid):
   req = {}
   req['p'] = request.args.get('p')
   req['ipp'] = request.args.get('ipp')
   out = learning_meteors_dataset(amsid, req)
   return out




@app.route('/API/<cmd>', methods=['GET', 'POST'])
def main_api(cmd):
   if cmd == 'crop_video':
      sd_video_file = request.args.get('video_file')
      x = request.args.get('x')
      y = request.args.get('y')
      w = request.args.get('w')
      h = request.args.get('h')
      out = crop_video(sd_video_file, x,y,w,h)
      resp = {}
      resp['status'] = 1
      return(resp)
   if cmd == 'edit_mask_points':
      mask_file = request.args.get('mask_file')
      if mask_file is None:
         mask_file = request.form.get('mask_file')
      action = request.args.get('action')
      mask_points = request.args.get('mask_points')
      
      out = edit_mask_points(mask_file,action,mask_points)
      #out = "OK"
      resp = {}
      resp['status'] = 1
      return(resp)

   if cmd == 'refit_meteor':
       
      sd_video_file = request.args.get('video_file')
      fn, dir = fn_dir(sd_video_file)
      cmd = "./Process.py refit_meteor " + fn
      os.system(cmd)
      resp = {}
      resp['status'] = 1
      return(resp)

   if cmd == 'update_meteor_points':
      if request.method == "GET":
         sd_video_file = request.args.get('sd_video_file')
         frames = request.args.get('frames')
         frames = json.loads(frames)
      else :
         sd_video_file = request.form.get('sd_video_file')
         frames = request.form.get('frames')
         frames = json.loads(frames)


      run = 1
      out = update_meteor_points(sd_video_file, frames)
   if cmd == 'show_cat_stars':
      run = 1
      video_file = request.args.get('video_file')
      hd_stack_file = request.args.get('hd_stack_file')
      points = request.args.get('points')
      out = show_cat_stars(video_file, hd_stack_file, points)

   if cmd == 'delete_meteor':
      run = 1
      #delete_meteor(amsid, data)

   if cmd == 'find_stars_in_pic':
      run = 1
      #find_stars_in_pic(amsid, data)
   if cmd == 'blind_solve':
      run = 1
      #blind_solve(amsid, data)
   if cmd == 'delete_cal':
      run = 1
      #delete_cal(amsid, data)

   return out 
