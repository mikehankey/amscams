import base64
import os
from flask import Flask, request, Response, make_response
from FlaskLib.Learning import learning_meteors_dataset, learning_meteors_tag, meteor_ai_scan, recrop_roi, learn_main, learning_review_day, batch_update_labels
from FlaskLib.motion_detects import motion_detects
from FlaskLib.FlaskUtils import get_template
from FlaskLib.api_funcs import update_meteor_points, show_cat_stars, delete_meteor, restore_meteor, delete_meteors, reduce_meteor, delete_frame, crop_video
from FlaskLib.calib_funcs import calib_main, cal_file, show_masks, del_calfile, lens_model, edit_mask, edit_mask_points, calib_main_new
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipePwdProtect import login_page, check_pwd_ajax
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page , pick_points, pick_points_day 
from FlaskLib.config_funcs import config_vars 
from FlaskLib.meteors_main import meteors_main , meteors_by_day, trash_page
from FlaskLib.super_stacks import stacks_main, stacks_day_hours, stacks_hour
from FlaskLib.min_detail import min_detail_main
from FlaskLib.live import live_view
from FlaskLib.TL import tl_menu 
from FlaskLib.man_reduce import meteor_man_reduce , save_man_reduce
from FlaskLib.man_detect import man_detect , import_meteor
from FlaskLib.meteors_main_redis import meteors_main_redis
#from FlaskLib.Maps import make_map 
from flask import redirect, url_for, abort
import json

from flask_httpauth import HTTPBasicAuth

app = Flask(__name__, static_url_path='/static')
auth = HTTPBasicAuth()

#, ssl_context=('cert.pem', 'key.pem'))

# Main controller for AllSkyCams UI application.

json_conf = load_json_file("../conf/as6.json")
if "dynamodb" in json_conf:
   dynDB = 1
   from flask_dynamo import Dynamo
   app.config['DYNAMO_TABLES'] = [
   {
      'TableName': 'station',
      'KeySchema': [dict(AttributeName='station_id', KeyType='HASH')],
      'AttributeDefinitions' : [dict(AttributeName='station_id', AttributeType='S')],
      'BillingMode': 'PAY_PER_REQUEST'
   },
   {
      'TableName': 'meteor_obs',
      'KeySchema': [dict(AttributeName='station_id', KeyType='HASH'),dict(AttributeName='sd_video_file', KeyType='RANGE')],
      'AttributeDefinitions': [dict(AttributeName='station_id', AttributeType='S'), dict(AttributeName='sd_video_file', AttributeType='S')],
      'BillingMode': 'PAY_PER_REQUEST'
   },
   {
      'TableName': 'x_meteor_event',
      'KeySchema': [dict(AttributeName='event_day', KeyType='HASH'),dict(AttributeName='event_id', KeyType='RANGE')],
      'AttributeDefinitions' : [dict(AttributeName='event_day', AttributeType='S'), dict(AttributeName='event_id', AttributeType='S')],
      'BillingMode': 'PAY_PER_REQUEST'
   }
   ]
   dynamo = Dynamo(app)



@auth.verify_password
def verify_password(username,password):
   json_conf = load_json_file("../conf/as6.json")
   if username == json_conf['site']['ams_id'] and password == json_conf['site']['pwd']:
      return(username)



@app.route('/TL/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def tlm(amsid):
   out = tl_menu(amsid)
   return(out)


@app.route('/msapi/', methods=['GET', 'POST'])
@auth.login_required
def msapi():
   from FlaskLib.meteor_scan_api import meteor_scan_api_controller

   jdata = request.get_json()

   print("JDATA", jdata, type(jdata))
   if jdata is None:
      jdata = {}
   print(jdata)
   out = meteor_scan_api_controller(jdata)
   return(out)


@app.route('/maps/', methods=['GET', 'POST'])
@auth.login_required
def map_runner():

   points = request.args.get('points')
   lines = request.args.get('lines')


   img = make_map(points, lines)
   response = make_response(img.getvalue())
   response.headers['Content-Type'] = 'image/png'
   response.headers['Content-Disposition'] = 'filename=%d.png' % 0
   return response


@app.route('/obs_review/<day>/', methods=['GET', 'POST'])
@auth.login_required
def obs_rev_control(day):
   from FlaskLib.Events import obs_review 
   resp = obs_review(day, json_conf)
   return(resp)


@app.route('/save_points/', methods=['GET', 'POST'])
@auth.login_required
def cntl_save_points():
   from FlaskLib.PointPicker import save_points

   jdata = request.get_json()
   data = jdata['data']
   file = jdata['file']
   station = jdata['station']
   print("FILE:", file)
   print("DATA:", data)
   #data = request.args.get('data')
   #file = request.args.get('file')


   resp = save_points(file,station,data,json_conf)
   return(resp)
@app.route('/pick_points/<meteor_id>/', methods=['GET', 'POST'])
@auth.login_required
def cntl_pick_points(meteor_id):
   el = meteor_id.split("_")
   if len(el) == 3:
      resp = pick_points_day(meteor_id,json_conf)
   else: 
      resp = pick_points(meteor_id,json_conf)
   return(resp)


@app.route('/point_picker/<date>/', methods=['GET', 'POST'])
@auth.login_required
def cntl_point_picker (date):
   from FlaskLib.PointPicker import point_picker 
   station = request.args.get('station')
   resp = point_picker(date,station, json_conf)
   return(resp)


@app.route('/kml_failed/<event_id>/', methods=['GET', 'POST'])
@auth.login_required
def event_kml_failed(event_id):
   from FlaskLib.EventViewer import EventViewer 
   EV = EventViewer(event_id=event_id)
   resp = EV.EVO.make_failed_kml()
   return Response(resp, mimetype='application/vnd.google-earth.kml+xml')


@app.route('/event_detail/<event_id>/', methods=['GET', 'POST'])
@auth.login_required
def event_detail_control(event_id):
   from FlaskLib.EventViewer import EventViewer 
   EV = EventViewer(event_id=event_id)
   resp = EV.EVO.render_template(template_file="FlaskTemplates/EventViewer.html")
   return(resp)


@app.route('/events/', methods=['GET', 'POST'])
@auth.login_required
def events_main_control():
   #from FlaskLib.Events import all_events 
   from Classes.Events import Events 
   fv = {}
   fv['solve_status'] = request.args.get('status')
   fv['start_date'] = request.args.get('start_date')
   fv['end_date'] = request.args.get('end_date')
   fv['stations'] = request.args.get('stations')
   EVS = Events(fv)
    
   EVS.load_events()
   resp = EVS.render_events_list()
   return(resp)

@app.route('/events/<date>/', methods=['GET', 'POST'])
@auth.login_required
def events_control(date):
   from FlaskLib.Events import list_events_for_day

   resp = list_events_for_day(date)
   return(resp)


@app.route('/', methods=['GET', 'POST'])
@auth.login_required
@auth.login_required
def main_menu():
   json_conf = load_json_file("../conf/as6.json")
   ams_id = json_conf['site']['ams_id']
   redir = "/stacks/" + ams_id + "/"
   return redirect(redir)


   out = login_page()
   header = get_template("FlaskTemplates/header-login.html")
   footer = get_template("FlaskTemplates/footer-remote.html")
   out = out.replace("{HEADER}", header)
   out = out.replace("{FOOTER}", footer)
   return out

@app.route('/api/check_login', methods=['GET', 'POST'])
@auth.login_required
def chk_login():
   user = request.args.get('user')
   passwd = request.args.get('pwd')
   out = check_pwd_ajax(user, passwd)
   return out


@app.route('/api/delete_frame/<meteor_file>/', methods=['GET', 'POST'])
@auth.login_required
def del_frame(meteor_file):
   fn = request.args.get('fn')
   out = delete_frame(meteor_file,fn)
   return out

@app.route('/save_man_reduce/', methods=['GET', 'POST'])
@auth.login_required
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
@auth.login_required
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


@app.route('/import_meteor/', methods=['GET', 'POST'])
@auth.login_required
def import_meteor_cntl():
   data = {}
   import_file = request.args.get('import_file')
   import_station = request.args.get('import_station')
   step = request.args.get('step')
   data['import_file'] = import_file
   data['import_station'] = import_station
   data['step'] = step
   out = import_meteor(data)
   return(out)

@app.route('/man_detect/<min_file>/', methods=['GET', 'POST'])
@auth.login_required
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
@auth.login_required
def red_meteor(meteor_file):
   out = reduce_meteor(meteor_file)
   return out

@app.route('/api/delete_meteor/<jsid>/', methods=['GET', 'POST'])
@auth.login_required
def del_meteor(jsid):
   data = {}
   data['data'] = request.args.get('data')
   out = delete_meteor(jsid, data)
   return out

@app.route('/api/restore_meteor/<jsid>/', methods=['GET', 'POST'])
@auth.login_required
def rest_meteor(jsid):
   data = {}
   data['data'] = request.args.get('data')
   out = restore_meteor(jsid, data)
   return out


@app.route('/api/delete_meteors/', methods=['GET', 'POST'])
@auth.login_required
def del_meteors():

   data = {}
   data['detections'] = request.form.get('detections')

   out = delete_meteors(data)
   return out

@app.route('/cal/lensmodel/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def lens_mod(amsid):
   out = lens_model(amsid)
   return out


@app.route('/cal/vars/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def op_vars(amsid):
   if request.method == "POST":
      data = request.form
   else:
      data = None
   out = config_vars(amsid,data)
   return out

@app.route('/cal/masks/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def masks(amsid):
   out = show_masks(amsid)
   return out

@app.route('/edit_mask/<amsid>/<camid>/', methods=['GET', 'POST'])
@auth.login_required
def emasks(amsid,camid):
   out = edit_mask(amsid,camid)
   return out


@app.route('/calfile/del/<amsid>/<calfile>/', methods=['GET', 'POST'])
@auth.login_required
def del_cfile(amsid, calfile):
   out = del_calfile(amsid, calfile)
   return out

@app.route('/calfile/<amsid>/<calfile>/', methods=['GET', 'POST'])
@auth.login_required
def cfile(amsid, calfile):
   out = cal_file(amsid, calfile)
   return out

@app.route('/calib_new/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def calib_new(amsid):
   req = {}
   req['cam_id_filter'] = request.args.get('cam_id_filter')
   out = calib_main_new(amsid,req)

@app.route('/calib/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def calib(amsid):
   req = {}
   req['cam_id_filter'] = request.args.get('cam_id_filter')
   out = calib_main(amsid,req)
   return out

@app.route('/live/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def live(amsid):
   out = live_view(amsid)
   return out

@app.route('/min_detail/<amsid>/<date>/<min_file>/', methods=['GET', 'POST'])
@auth.login_required
def min_detail(amsid, date, min_file):
   out = min_detail_main(amsid, date, min_file)
   return out


@app.route('/stacks_hour/<amsid>/<date>/<hour>/', methods=['GET', 'POST'])
@auth.login_required
def stacks_day_hour(amsid, date, hour):
   #req = {}
   #req['hour'] = request.args.get('hour')
   out = stacks_hour(amsid, date, hour)
   return out


@app.route('/stacks_day/<amsid>/<date>/', methods=['GET', 'POST'])
@auth.login_required
def stacks_day(amsid, date):
   req = {}
   req['hour'] = request.args.get('hour')
   out = stacks_day_hours(amsid, date, req)
   return out


@app.route('/stacks/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
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
   req['stack_type'] = request.args.get('stack_type')

   out = stacks_main(amsid,req)
   return(out)




@app.route('/meteors_by_day/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def meteors_bd(amsid ):
   req = {}
   out = meteors_by_day(amsid,req)
   return(out)


# TRASH PAGE
@app.route('/trash/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def trash_pg(amsid ):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   rebuild = request.args.get('rebuild')
   req = {}
   if rebuild is not None:
      req['rebuild'] = 1
   req['start_day'] = start_day
   req['end_day'] = end_day
   out = trash_page(amsid, req)
   return(out)


# REDIS MAIN
@app.route('/rmeteor/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def rmeteors(amsid ):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   meteor_per_page = request.args.get('meteor_per_page')
   sort_by = request.args.get('sort_by')
   filterd = request.args.get('filter')
   ai_list = request.args.get('ai_list')
   p = request.args.get('p')

   req['start_day'] = start_day
   req['end_day'] = end_day
   req['meteor_per_page'] = meteor_per_page
   req['p'] = p
   req['sort_by'] = sort_by 
   req['filter'] = filterd
   req['ai_list'] = ai_list

   out = meteors_main_redis(amsid,req, json_conf)

   return(out)

# MAIN METEOR PAGE
@app.route('/meteor/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def meteors(amsid ):
   req = {}
   start_day = request.args.get('start_day')
   end_day = request.args.get('end_day')
   meteor_per_page = request.args.get('meteor_per_page')
   sort_by = request.args.get('sort_by')
   filter = request.args.get('filter')
   ai_list = request.args.get('ai_list')
   p = request.args.get('p')

   req['start_day'] = start_day
   req['end_day'] = end_day
   req['meteor_per_page'] = meteor_per_page
   req['p'] = p
   req['sort_by'] = sort_by 
   req['filter'] = filter
   req['ai_list'] = ai_list
   out = meteors_main(amsid,req)

   return out

@app.route('/goto/meteor/<meteor_file>/', methods=['GET', 'POST'])
@auth.login_required
def goto_meteor(meteor_file):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   date = meteor_file[0:10] 
   out = detail_page(amsid, date, meteor_file )
   return out

@app.route('/meteor/<amsid>/<date>/<meteor_file>/', methods=['GET', 'POST'])
@auth.login_required
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out

@app.route('/LEARNING/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def lrn_main(amsid):
   out = learn_main(amsid)
   return(out)

@app.route('/LEARNING/<amsid>/BATCH_UPDATE/', methods=['GET', 'POST'])
@auth.login_required
def lrn_batch_up(amsid):
   jdata = request.get_json()
   label_data = jdata['label_data']
   print(label_data) 
   out = batch_update_labels(amsid, label_data)
   out = "OK"
   return(out)



@app.route('/LEARNING/<amsid>/RECROP/', methods=['GET', 'POST'])
@auth.login_required
def lrn_recrop(amsid):
   jdata = request.get_json()
   stack_fn = jdata['stack_fn']
   div_id = jdata['div_id']
   click_x = jdata['click_x']
   click_y = jdata['click_y']
   print("DATA", amsid, stack_fn, div_id, click_x, click_y)
   out = recrop_roi(amsid, stack_fn, div_id, click_x, click_y)
   return(out)


@app.route('/LEARNING/<ams_id>/AI_SCAN/<label>', methods=['GET', 'POST'])
@auth.login_required
def lrn_ai_scan(ams_id, label):
   req = {}
   p = request.args.get('p')
   ipp = request.args.get('ipp')
   if p is None:
      req['p'] = 1 
   else:
      req['p'] = p
   if ipp is None:
      req['ipp'] = 1000 
   else:
      req['ipp'] = ipp
   req['ams_id'] = ams_id
   req['label'] = label 
   out = meteor_ai_scan(req, json_conf)
   return out


@app.route('/LEARNING/<amsid>/review/', methods=['GET', 'POST'])
@auth.login_required
def lrn_review(amsid):
   req = {}
   req['date'] = request.args.get('date')
   out = learning_review_day(amsid, req['date'])
   return out


@app.route('/LEARNING/TAG/<label>', methods=['GET', 'POST'])
@auth.login_required
def lrn_tag(label):
   req = {}
   req['learning_file'] = request.args.get('learning_file')
   out = learning_meteors_tag(label, req)
   return out

@app.route('/LEARNING/<amsid>/<label>', methods=['GET', 'POST'])
@auth.login_required
def lrn_meteors(amsid,label ):
   req = {}
   req['sort'] = request.args.get('sort')
   req['filter_date'] = request.args.get('filter_date')
   req['filter_station'] = request.args.get('filter_station')
   req['p'] = request.args.get('p')
   req['ipp'] = request.args.get('ipp')
   req['label'] = label
   out = learning_meteors_dataset(amsid, req)
   return out


@app.route('/motion/<date>/', methods=['GET', 'POST'])
@auth.login_required
def cnt_motion(date):
   out = motion_detects(date)
   return(out)


@app.route('/API/<cmd>', methods=['GET', 'POST'])
@auth.login_required
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
