#!/usr/bin/python3

import os
import cgi 
import json

JSON_CONFIG = '/home/ams/amscams/conf/as6.json'

print('Content-Type: text/html; charset=utf-8')

def api_controller(form):
   api_function = form.getvalue('function')

   if(api_function=='login'):
      login(form)


# LOGIN
def login(form):

   user = form.getvalue('user')
   password = form.getvalue('pwd')

   if(user is not None and password is not None):
      json_file = open('JSON_CONFIG')
      json_str = json_file.read()
      json_data = json.loads(json_str)
       
      try:
         if(json_data['site']['ams_id']==user and json_data['site']['pwd']==pwd):
               result['passed'] = 1
         else:
               result['passed'] = 0
      except Exception:
         result['passed'] = 0
    


# MAIN
form = cgi.FieldStorage()
api_controller(form)
