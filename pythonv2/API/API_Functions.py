import json
import sys

from API_Tools import *

def delete_detection(form):
   detect = form.getValue('detect')

   if(detect is None):
      send_error_message('You need to enter the ID of the detection.')
   else:
      print("DELETE " + detect)
