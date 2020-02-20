import json
import sys
import cgitb
 

def send_error_message(msg): 
   cgitb.enable()
   print(json.dumps({'error':msg}))
   sys.exit(0)