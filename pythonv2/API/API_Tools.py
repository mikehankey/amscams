import json
import sys
import cgitb 

API_URL = 'https://sleaziest-somali-2255.dataplicity.io/pycgi/webUI.py?cmd=API'     

def send_json(json_msg):
   print(json_msg) 


def send_error_message(msg):  
   send_json(json.dumps({'error':msg}))
   sys.exit(0)