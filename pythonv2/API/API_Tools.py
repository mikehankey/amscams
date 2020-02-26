import json
import sys
import cgitb 

 

def send_json(json_msg): 
   print(json_msg) 


def send_error_message(msg,log=False):

   # It's a login issue
   if(log is True): 
      send_json(json.dumps({'error':msg,'login':1}))
   else:
      send_json(json.dumps({'error':msg}))
  
   sys.exit(0)