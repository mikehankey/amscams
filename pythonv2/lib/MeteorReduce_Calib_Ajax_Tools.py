import cgitb
 
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

   json_file = fix_old_file_name(json_file)
   print(json_file)   
   

