import json
import sys
import cgitb

from API_Tools import *

def delete_detection(form):
   
   cgitb.enable()
   try:
      detect = form.getValue('detect')
   except:
      send_error_message('You need to enter the ID of the detection.')
    