#!/usr/bin/python3

import os
import cgi 
import cgitb
import string
import random
import json
import datetime

from os import environ 

JSON_CONFIG = '/home/ams/amscams/conf/as6.json' 

def api_controller(form):
   api_function = form.getvalue('function')

   if(api_function=='login'):
      print(API_login(form))


# LOGIN
def API_login(form):

   cgitb.enable()

   user = form.getvalue('user').strip()
   password = form.getvalue('pwd').strip()

   test_log = False

   if(user is not None and password is not None):
      json_file = open(JSON_CONFIG)
      json_str = json_file.read()
      json_data = json.loads(json_str)
 
      try:
         if(json_data['site']['ams_id']==user and json_data['site']['pwd']==password):
            test_log = True
      except Exception:
         test_log = False
   

   if(test_log is True):
      _date, tok = create_token() 

      # Add the token to the current list of available token
      write_new_access(user,tok,_date)

      return json.dumps({'token':tok,'expire':_date})
   else:
      return json.dumps({'error':'You are not authorized'})


   return test_log



# Write new access
def write_new_access(user,tok,_date):
   f = open(user+"_log.log","a+")
   f.write(tok + " " _date + "\r\n")
   f.close()



# CREATE TEMPORARY TOKEN
def create_token():
 
   # Expired in one hour
   expiration = datetime.datetime.now() + datetime.timedelta(hours=1)
   
   # Create Token
   tok = expiration.strftime("%d%b%Y%H%M%S_4llsk")  + ''.join(random.choice('AbcDeFghIJklmNOpqRstUVWxYZ;?._!') for _ in range(18))
   
   return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),tok

 

# TEST API LOGIN COOKIE
def test_api_login_cookie(_val):
   
   if environ.has_key('HTTP_COOKIE'):  
      for cookie in map(strip, split(environ['HTTP_COOKIE'], ';')):
         (key, value ) = split(cookie, '=');
         if key == "api_tok" and value == _val:
            return True

   return False 

 