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
PATH_ACCESS_LOGS = '/home/ams/amscams/pythonv2/API'

def api_controller(form):
   api_function = form.getvalue('function')
   tok = form.getvalue('tok') 

   if(api_function=='login'):
      print(API_login(form))
   else:
      # For everything else, we need to have a token passed
      test_api_login(tok)
      sys.exit()


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



# Write new access in proper file
def write_new_access(user,tok,_date):
   f = open(PATH_ACCESS_LOGS + os.sep + "access.log","a+")
   f.write(tok + " " + _date + "\r\n")
   f.close()



# CREATE TEMPORARY TOKEN
def create_token():
 
   # Expired in one hour
   expiration = datetime.datetime.now() + datetime.timedelta(hours=1)
   
   # Create Token
   tok = expiration.strftime("%d%b%Y%H%M%S_4llsk")  + ''.join(random.choice('AbcDeFghIJklmNOpqRstUVWxYZ;?._!') for _ in range(18))
   
   return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),tok

 

# TEST API LOGIN  
def test_api_login(tok):
   
   # Open the corresponding file
   with open(PATH_ACCESS_LOGS + os.sep + "access.log") as f:
    lines = [line.rstrip() for line in f]
   
   print(lines)

   

   