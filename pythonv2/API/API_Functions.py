import json
import sys
import cgitb

from API_Tools import *

def delete_detection(form):
   
   cgitb.enable()
   detect = form.getValue('detect')

   if(detect is None):
      send_error_message('You need to enter the ID of the detection.')
   else:
      print("DELETE " + detect)
