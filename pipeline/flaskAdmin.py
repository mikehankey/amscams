import base64
import os
from flask import Flask, request, Response, make_response
from FlaskLib.Learning import learning_meteors_dataset, learning_meteors_tag, meteor_ai_scan, recrop_roi, recrop_roi_confirm, learn_main, learning_review_day, batch_update_labels, learning_db_dataset, timelapse_main, learning_weather, ai_review, ai_rejects, confirm_meteor, confirm_non_meteor, confirm_non_meteor_label , ai_main , ai_dict, ai_scan_review,ai_non_meteors , export_samples, move_ai_sample
#from FlaskLib.AI_API import ai_api
from FlaskLib.motion_detects import motion_detects
from FlaskLib.FlaskUtils import get_template
from FlaskLib.api_funcs import update_meteor_points, show_cat_stars, delete_meteor, restore_meteor, delete_meteors, reduce_meteor, delete_frame, crop_video, update_meteor_cal_params
from FlaskLib.calib_funcs import calib_main, cal_file, show_masks, del_calfile, lens_model, edit_mask, edit_mask_points, calib_main_new
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipePwdProtect import login_page, check_pwd_ajax
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page , pick_points, pick_points_day 
from FlaskLib.config_funcs import config_vars , network_setup 
from FlaskLib.meteors_main import meteors_main , meteors_by_day, trash_page, non_meteors_main, confirm_non_meteors, confirm_all_trash 
from FlaskLib.super_stacks import stacks_main, stacks_day_hours, stacks_hour
from FlaskLib.min_detail import min_detail_main, join_min_files
from FlaskLib.live import live_view
from FlaskLib.TL import tl_menu 
from FlaskLib.man_reduce import meteor_man_reduce , save_man_reduce
from FlaskLib.man_reduce_v2 import meteor_man_reduce_v2 , save_man_reduce_v2
from FlaskLib.man_detect import man_detect , import_meteor
from FlaskLib.meteors_main_redis import meteors_main_redis
from FlaskLib.network import network_main , network_map, network_meteors, network_events
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




@app.route('/astroAPI/', methods=['POST', 'GET'])
def astAPI():
   from werkzeug.utils import secure_filename
   from werkzeug.datastructures import  FileStorage

   temp_dir = "/mnt/ams2/astroTemp/"
   if os.path.exists(temp_dir) is False:
      os.makedirs(temp_dir)
   app.config['UPLOAD_FOLDER'] = "/mnt/ams2/astroTEMP/"

   if request.method == 'POST':
      f = request.files['file']
      print("FILE:", f.filename)
      f.save(secure_filename(f.filename))
      os.system("mv " + f.filename + " " + temp_dir)
      out = 'file uploaded successfully <br><img src=/astroTemp/' + f.filename + '>'
      plate_file = temp_dir + f.filename
      solved_file = temp_dir + f.filename + ".solved"
      astrout = temp_dir + f.filename + ".txt"
      HD_W = "1920"
      HD_H = "1080"
      cmd = "/usr/local/astrometry/bin/solve-field " + plate_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(HD_W) + " --height=" + str(HD_H) + " -d 1-40 --scale-units dw --scale-low 60 --scale-high 120 -S " + solved_file + " >" + astrout
      out += "<br>"
      out += cmd
      return(out)
   else:
      out = """
         <html>
            <body>
               Upload a star file.  NOTE: Star file must follow naming convention starting with AMSXX_YYYY_MM_DD_HH_SS_MM_000_CAMID-trim-####.png (or jpg). 
               <form action = "/astroAPI/" method = "POST" 
                  enctype = "multipart/form-data">
                  <input type = "file" name = "file" /><br>
                  <input type = "submit"/>
               </form>   
            </body>
         </html>
      """
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

@app.route('/save_man_reduce_v2/', methods=['GET', 'POST'])
@auth.login_required
def save_man_redv2():
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
   out = save_man_reduce_v2(data)
   return(out)   

@app.route('/meteor_man_reduce_v2/', methods=['GET', 'POST'])
@auth.login_required
def meteor_man_redv2():
  
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
   out = meteor_man_reduce_v2(meteor_file, x,y,w,h,step,first_frame,last_frame,ScaleFactor)
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
   out = lens_model(amsid, json_conf)
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


@app.route('/network/setup/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def net_set(amsid):
   print("M", request.method)
   if request.method == "POST":
      data = {} 
      for key, value in request.form.items():
         data[key] = value
      data['method'] = "POST"
   else:
      data = {} 
   out = network_setup(amsid,data)
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



@app.route('/join_min_files/<amsid>/<min_file>/', methods=['GET', 'POST'])
@auth.login_required
def join_mfiles(amsid, min_file):
   next_file = request.args.get('next_file')
   seconds = request.args.get('seconds')
   out = join_min_files(amsid, min_file, next_file, seconds)
   return out

@app.route('/min_detail/<amsid>/<date>/<min_file>/', methods=['GET', 'POST'])
@auth.login_required
def min_detail(amsid, date, min_file):
   label = request.args.get('label')
   out = min_detail_main(amsid, date, min_file, label)
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

# MAIN NON METEOR PAGE
@app.route('/confirm_all_trash/<station_id>/<date>/', methods=['GET', 'POST'])
@auth.login_required
def ctrash(station_id, date):
   out = confirm_all_trash(station_id, date)
   return(out)




@app.route('/confirm_non_meteors/', methods=['GET', 'POST'])
@auth.login_required
def cnon_meteors():
   req = {}
   all_ids = request.args.get('all_ids')
   if all_ids is None:
      all_ids = request.form.get('all_ids')
   out = confirm_non_meteors(all_ids, json_conf)
   return(out)

@app.route('/non_meteors/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def non_meteors(amsid ):
   req = {}
   date = request.args.get('date')
   req['date'] = date 
   out = non_meteors_main(amsid,req,json_conf)
   return out
   

# MAIN METEOR PAGE
@app.route('/meteor/<amsid>/<start_day>/', methods=['GET', 'POST'])
@auth.login_required
def meteors_shortcut(amsid,start_day ):

   req = {}
   #start_day = request.args.get('start_day')
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


@app.route('/TL/<amsid>/<date>/<cam_num>/', methods=['GET', 'POST'])
@auth.login_required
def tl_main(amsid,date,cam_num):
   out = timelapse_main(amsid,date,cam_num, json_conf)
   return(out)



@app.route('/DASHBOARD/<amsid>/<subcmd>', methods=['GET', 'POST'])
@auth.login_required
def lrn_dash_sub(amsid, subcmd):
   from FlaskLib.Dashboard import Dashboard
   from FlaskLib.DashMeteors import MeteorDash
   from FlaskLib.DashWeather import WeatherDash
   from FlaskLib.DashLearning import LearningDash
   from FlaskLib.DashCalibration import CalibrationDash
   from FlaskLib.DashSystem import SystemDash
   from FlaskLib.DashConfig import ConfigDash 
   in_data = {}
   for key, value in request.args.items():
      in_data[key] = value
   if "cmd" not in in_data:
      in_data['cmd'] = None 
   if subcmd == "METEORS":
      MD = MeteorDash()
      return(MD.meteors_main(in_data))
   if subcmd == "WEATHER":
      WT = WeatherDash()
      return(WT.weather_main(in_data))
   if subcmd == "LEARNING":
      LRN = LearningDash()
      return(LRN.learning_main(in_data))


   if subcmd == "CALIBRATION":
      CB = Calibration()
      return(CB.calibration_main(in_data))
   if subcmd == "SYSTEM":
      SYS = System()
      return(SYS.system_main(in_data))
   if subcmd == "CONFIG":
      CFG = Config()
      return(CFG.config_main(in_data))

@app.route('/DASHBOARD/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def lrn_dash(amsid):
   from FlaskLib.Dashboard import Dashboard
   from FlaskLib.DashMeteors import MeteorDash
   from FlaskLib.DashWeather import WeatherDash
   from FlaskLib.DashLearning import LearningDash
   from FlaskLib.DashCalibration import CalibrationDash
   from FlaskLib.DashSystem import SystemDash
   from FlaskLib.DashConfig import ConfigDash

   Dash = Dashboard()


   in_data = {}
   for key, value in request.args.items():
      in_data[key] = value
   in_data['station_id'] = amsid

   out = Dash.controller(in_data)
   return(out)


@app.route('/NETWORK/EVENTS/<amsid>/<date>/', methods=['GET', 'POST'])
@auth.login_required
def net_events(amsid, date):
   out = network_events(amsid, date, json_conf)
   return(out)


@app.route('/NETWORK/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def net_main(amsid):
   out = network_main(amsid, json_conf)
   return(out)

@app.route('/NETWORK/MAP/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def net_map(amsid):
   out = network_map(amsid, json_conf)
   return(out)

@app.route('/NETWORK/METEORS/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def net_met(amsid):
   day = request.args.get("day")
   in_data = {}
   in_data['day'] = day
   out = network_meteors(amsid, json_conf, in_data)
   return(out)



@app.route('/LEARNING/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def lrn_main(amsid):
   out = learn_main(amsid)
   return(out)

@app.route('/AIREVIEW/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def air(amsid):
   options = {}
   for key, value in request.args.items():
      options[key] = value
   out = ai_review(amsid, options, json_conf)
   return(out)


@app.route('/AI/API/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def aiapi(amsid):

   for key, value in request.args.items():
      options[key] = value
   out = ai_api(amsid, options, json_conf, ASAI)
   return(out)

@app.route('/AI/DICT/<amsid>/<date>/', methods=['GET', 'POST'])
@auth.login_required
def aidict(amsid, date):
   options = {}
   for key, value in request.args.items():
      options[key] = value
   out = ai_dict(amsid, date, options, json_conf)
   return(out)


@app.route('/AI/SS/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def aiss(amsid):
   options = {}
   for key, value in request.args.items():
      options[key] = value
   out = ai_scan_review(amsid, options, json_conf)
   return(out)

@app.route('/move_ai_sample/', methods=['GET', 'POST'])
@auth.login_required
def mv_sample():
   options = {}
   if request.method == "POST":
      for key, value in request.form.items():
         options[key] = value
      options['method'] = "POST"
   else:
      for key, value in request.args.items():
         options[key] = value
   out = move_ai_sample(options, json_conf)
   return(out)


@app.route('/AI/MAIN/EXPORT/SAMPLES/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def exp_samples(amsid):
   options = {}
   if request.method == "POST":
      for key, value in request.form.items():
         options[key] = value
      options['method'] = "POST"
   else:
      for key, value in request.args.items():
         options[key] = value
   out = export_samples(amsid, options, json_conf)
   return(out)


@app.route('/AI/MAIN/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def aimain(amsid):
   out = ai_main(amsid, json_conf)
   return(out)

@app.route('/AIREJECTS/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def airej(amsid):
   options = {}
   for key, value in request.args.items():
      options[key] = value
   out = ai_rejects(amsid, options, json_conf)
   return(out)

@app.route('/AI/NON_METEORS/<amsid>/', methods=['GET', 'POST'])
@auth.login_required
def ainm(amsid):
   options = {}
   for key, value in request.args.items():
      options[key] = value
   out = ai_non_meteors(amsid, options, json_conf)
   return(out)




@app.route('/confirm_meteor/<root_fn>/', methods=['GET'] )
@auth.login_required
def hconfirm(root_fn):
   out = confirm_meteor(json_conf['site']['ams_id'], root_fn )
   return(out)

@app.route('/confirm_non_meteor/<root_fn>/', methods=['GET'] )
@auth.login_required
def confirm_nm(root_fn):
   out = confirm_non_meteor(json_conf['site']['ams_id'], root_fn )
   return(out)

@app.route('/confirm_non_meteor_label/<root_fn>/', methods=['GET'] )
@auth.login_required
def conf_mc(root_fn):
   label = request.args.get('label')
   out = confirm_non_meteor_label(json_conf['site']['ams_id'], root_fn , label)
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
   print("JDATA:", jdata)
   stack_fn = jdata['stack_fn']
   div_id = jdata['div_id']
   click_x = jdata['click_x']
   click_y = jdata['click_y']
   size = jdata['size']
   print("DATA", amsid, stack_fn, div_id, click_x, click_y)
   out = recrop_roi(amsid, stack_fn, div_id, click_x, click_y,size)
   return(out)


@app.route('/LEARNING/<amsid>/RECROP_CONFIRM/', methods=['GET', 'POST'])
@auth.login_required
def lrn_recrop_confirm(amsid):
   jdata = request.get_json()
   station_id = jdata['station_id']
   root_file = jdata['root_file']
   roi = jdata['roi']
   out = recrop_roi_confirm(station_id, root_file, roi)
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


@app.route('/LEARNING/<amsid>/WEATHER/<label>', methods=['GET', 'POST'])
@auth.login_required
def lrn_weather(amsid,label ):
   req = {}
   req['label'] = label
   out = learning_weather(amsid, req)
   return out
   

@app.route('/LEARNING/<amsid>/<label>', methods=['GET', 'POST'])
@auth.login_required
def lrn_meteors(amsid,label ):
   req = {}
   req['sort'] = request.args.get('sort')
   req['filter_date'] = request.args.get('filter_date')
   req['filter_station'] = request.args.get('filter_station')
   req['conf'] = request.args.get('conf')
   req['p'] = request.args.get('p')
   req['ipp'] = request.args.get('ipp')
   req['label'] = label
   req['station_id'] = amsid
   req['datestr'] = request.args.get('datestr')
   req['human_confirmed'] = request.args.get('human_confirmed')
   req['station_id'] = amsid

   if req['p'] is None:
      req['p'] = 0
   if req['ipp'] is None:
      req['ipp'] = 100

   #out = learning_meteors_dataset(amsid, req)
   out = learning_db_dataset(amsid, req)
   return out


@app.route('/motion/<date>/', methods=['GET', 'POST'])
@auth.login_required
def cnt_motion(date):
   out = motion_detects(date)
   return(out)


@app.route('/API/<cmd>', methods=['GET', 'POST'])
@auth.login_required
def main_api(cmd):

   if cmd == 'swap_calib':
      cal_file = request.args.get("cal_file")
      meteor_file = request.args.get("meteor_file")
      resp = update_meteor_cal_params(meteor_file, cal_file, json_conf)
      if "GOOD" in resp['msg']:
         station_id = json_conf['site']['ams_id'] 
         date = meteor_file[0:10] 

         rurl = "/meteor/{:s}/{:s}/{:s}/".format(station_id, date, meteor_file.replace(".json", ".mp4"))

         return redirect(rurl, code=301)
      return(resp)

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
      #cmd = "./Process.py refit_meteor " + fn
      cmd = "./recal.py refit_meteor " + fn
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
