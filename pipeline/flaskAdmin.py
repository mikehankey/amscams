from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from FlaskLib.api_funcs import update_meteor_points
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page
app = Flask(__name__, static_url_path='/static')
import json


@app.route('/')
def main_menu():
   return 'Main Menu!'


@app.route('/meteors/<amsid>/<date>/<meteor_file>/', methods=['GET', 'POST'])
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out


@app.route('/API/<cmd>', methods=['GET', 'POST'])
def main_api(cmd):
   if cmd == 'delete_meteor':
      run = 1
      #delete_meteor(amsid, data)
   if cmd == 'update_meteor_points':
      if request.method == "GET":
         sd_video_file = request.args.get('sd_video_file')
         frames = request.args.get('frames')
         frames = json.loads(frames)
      else :
         data = request.form.get('sd_video_file')
         frames = request.form.get('frames')
         frames = json.loads(frames)


      run = 1
      out = update_meteor_points(sd_video_file, frames)
   if cmd == 'update_user_stars':
      run = 1
      #update_user_stars(amsid, data)
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
   #return out
