from flask import Flask, request
from FlaskLib.FlaskUtils import get_template
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
from FlaskLib.meteor_detail_funcs import detail_page
app = Flask(__name__, static_url_path='/static')



@app.route('/')
def main_menu():
   return 'Main Menu!'


@app.route('/meteors/<amsid>/<date>/<meteor_file>/', methods=['GET'], ['POST'])
def meteor_detail_page(amsid, date, meteor_file):
   out = detail_page(amsid, date, meteor_file )
   return out


@app.route('/api/<amsid>/<cmd>', methods=['GET'], ['POST'])
def api(amsid, cmd):
   data = request.data
   if cmd == 'delete_meteor':
      run = 1
      #delete_meteor(amsid, data)
   if cmd == 'update_meteor_points':
      run = 1
      #update_meteor_points(amsid, data)
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
