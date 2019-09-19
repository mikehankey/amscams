import cgitb

from lib.FileIO import load_json_file
from lib.MeteorReduce_Tools import name_analyser  
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.MeteorManualReducePage import fix_old_file_name

# Return Ra/Dec based on X,Y  
def getRADEC(form):
   # Debug
   cgitb.enable() 

   json_file = form.getvalue('json_file') 
   x = form.getvalue('x')
   y = form.getvalue('y')
   
   json = load_json_file(json_file)
  

   # Test if we have an old or a new JSON
   if "reduced_stack" in json:
      print("YES")
      # It's an old we need to create the right calib json object
      #new_json_content = {'calib'  : {  'device': { 'scale_px': json['pixscale'] }    }      }
      #print(new_json_content)
      #x_poly_fwd  = json_file['calib']['device']['poly']['x_fwd']
      #y_poly_fwd  = json_file['calib']['device']['poly']['y_fwd']
      #lat         = float(json_file['calib']['device']['lat'])
      #lon         = float(json_file['calib']['device']['lng'])
      #dec_d       = float(json_file['calib']['device']['center']['dec']) 
      #RA_d        = float(json_file['calib']['device']['center']['ra']) 
      #angle       =  float(json_file['calib']['device']['angle']) 
   #else:
      #print("NICE JSON")


   #json_file = fix_old_file_name(json_file)
   #print(json_file)   
   

