import cgitb
import json 

from lib.FileIO import load_json_file
from lib.MeteorReduce_Tools import name_analyser  
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.MeteorManualReducePage import get_new_calib
from lib.Old_JSON_conveter import fix_old_file_name, get_new_calib



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
      new_json_content = get_new_calib(json_f)
   else:
      new_json_content = json_f
   
   # Eventually fix the name to be able to parse it
   json_file_x = fix_old_file_name(json_file)
   
   # Compute the data with XYtoRADec
   results = [];

   for v in _values:
      x,y,ra,dec,az,el = XYtoRADec(v['x_HD'],v['y_HD'],name_analyser(json_file_x),new_json_content)
      results.append({'x_HD': v['x_HD'], 'y_HD': v['y_HD'],'y_org': v['y_org'], 'x_org': v['x_org'], 'ra':ra,'dec':dec,'az':az,'el':el})


   # Return JSON
   print(json.dumps({'res':results}))
   

