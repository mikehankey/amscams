import json
import sys


def it_is_json():
   print("Content-type: application/json\n\n")


def send_error_message(msg):
   it_is_json()
   print(json.dumps({'error':msg}))
   sys.exit(0)