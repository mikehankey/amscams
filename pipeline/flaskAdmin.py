
from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from FlaskLib.api_funcs import update_meteor_points, show_cat_stars, delete_meteor, delete_meteors, reduce_meteor, delete_frame
from FlaskLib.calib_funcs import calib_main, cal_file, show_masks
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipePwdProtect import login_page, check_pwd_ajax
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page 
from FlaskLib.meteors_main import meteors_main 
from FlaskLib.super_stacks import stacks_main, stacks_day_hours, stacks_hour
from FlaskLib.min_detail import min_detail_main
from FlaskLib.live import live_view
app = Flask(__name__, static_url_path='/static')
import json

# Main controller for AllSkyCams UI application.

@app.route('/')
def main_menu():
   out = login_page()
   header = get_template("FlaskTemplates/header-login.html")
   footer = get_template("FlaskTemplates/footer.html")
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

@app.route('/api/delete_meteors/', methods=['GET', 'POST'])
def del_meteors():

   data = {}
   data['detections'] = request.form.get('detections')

   out = delete_meteors(data)
   return out


@app.route('/cal/masks/<amsid>/', methods=['GET', 'POST'])
def masks(amsid):
   out = show_masks(amsid)
   return out

@app.route('/calfile/<amsid>/<calfile>/', methods=['GET', 'POST'])
def cfile(amsid, calfile):
   out = cal_file(amsid, calfile)
   return out


@app.route('/calib/<amsid>/', methods=['GET', 'POST'])
def calib(amsid):
   out = calib_main(amsid)
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

   out = stacks_main(amsid,req)
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

@app.route('/meteors/<amsid>/<date>/<meteor_file>/', methods=['GET', 'POST'])
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out


@app.route('/API/<cmd>', methods=['GET', 'POST'])
def main_api(cmd):
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
