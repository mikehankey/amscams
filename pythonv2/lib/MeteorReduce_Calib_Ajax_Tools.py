import cgitb
import json 

from lib.FileIO import load_json_file
from lib.MeteorReduce_Tools import name_analyser  
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.MeteorManualReducePage import fix_old_file_name

# Return Ra/Dec based on X,Y  
def getRADEC(form):
   # Debug
   cgitb.enable() 

   json_file = form.getvalue('json_file') 

   # Get all values
   values = form.getvalue('values')
   _values = json.loads(values)

   json_f = load_json_file(json_file)
   
   # Test if we have an old or a new JSON
   if "reduced_stack" in json_f:
      
      # It's an old we need to create the right calib json object
      new_json_content = { "calib":  
        { "device": {
            "alt":  float(json_f['cal_params']['device_alt']),
            "lat":  float(json_f['cal_params']['device_lat']),
            "lng":  float(json_f['cal_params']['device_lng']),
            "scale_px":  float(json_f['cal_params']['pixscale']),
            "poly": {
                "y_fwd": json_f['cal_params']['y_poly_fwd'],
                "x_fwd": json_f['cal_params']['x_poly_fwd']
            },
            "center": {
                "az": float(json_f['cal_params']['orig_az_center']),  
                "ra": float(json_f['cal_params']['orig_ra_center']), 
                "el": float(json_f['cal_params']['orig_el_center']),
                "dec": float(json_f['cal_params']['orig_dec_center']) 
            },
            "angle":  float(json_f['cal_params']['orig_pos_ang'])
         }      
      }}
   else:
      new_json_content = json_f
   
   json_file_x = fix_old_file_name(json_file)
   
   # Get the data
   #x,y,RA,dec,az,el = XYtoRADec(x,y,name_analyser(json_file_x),new_json_content)
   results = [];

   for v in _values:
      x,y,ra,dec,az,el = XYtoRADec(v['x_HD'],v['y_HD'],name_analyser(json_file_x),new_json_content)
      results.append({'x_HD': v['x_HD'], 'y_HD': v['y_HD'],'y_org': v['y_org'], 'x_org': v['x_org'], 'ra':ra,'dec':dec,'az':az,'el':el})


   # Return JSON
   print(json.dumps({'res':results}))
   

