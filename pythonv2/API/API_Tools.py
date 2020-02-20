import json
import sys

def send_error_message(msg):
  print(json.dumps({'error':msg}))
  sys.exit(0)