#!/usr/bin/python3

import os
import cgi 
import json
import datetime

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

   test_log = False

   if(user is not None and password is not None):
      json_file = open('JSON_CONFIG')
      json_str = json_file.read()
      json_data = json.loads(json_str)
       
      try:
         if(json_data['site']['ams_id']==user and json_data['site']['pwd']==pwd):
            test_log = True
      except Exception:
         test_log = False
   

   if(test_log is True):
      return json.dumps({'tok':create_token()})
   else
      return json.dumps({'error':'You are not authorized'})


   return test_log

# CREATE TEMPORARY TOKEN
def create_token():
   expiration = datetime.datetime.now() + datetime.timedelta(days=0.5)
   return expiration.strftime("%d%b%Y%H%M%S_4llsk") 


# MAIN
form = cgi.FieldStorage()
api_controller(form)
