import json
import sys
import cgitb 

 

def send_json(json_msg): 
   print(json_msg) 


def send_error_message(msg):  
   send_json(json.dumps({'error':msg}))
   sys.exit(0)