#!/usr/bin/python3

import os
import cgi 
import sys
import cgitb
import string
import random
import json 
 
from datetime import datetime
from os import environ 

from API.API_Tools import *
from API.API_Functions import *

JSON_CONFIG = '/home/ams/amscams/conf/as6.json' 
PATH_ACCESS_LOGS = '/home/ams/amscams/pythonv2/API'
ACCESS_FILE = PATH_ACCESS_LOGS + os.sep + "access.log"

def api_controller(form):
   api_function = form.getvalue('function')
   tok = form.getvalue('tok') 

   # Login
   if(api_function=='login'):
      print(API_login(form))
   else:
      # For everything else, we need to have a token passed
      if(test_api_login(tok)==False):
         send_error_message('You are not authorized')
      else:
         if(api_function=='delete'):
            print("DELETE")


# LOGIN
def API_login(form):

   cgitb.enable() 

   user = form.getvalue('user') 
   password = form.getvalue('pwd')
   
   if(user is not None and password is not None):
      user = user.strip() 

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
         return send_error_message('You are not authorized')

   else:
         return send_error_message('You need send a username and a password.')

   return test_log



# Write new access in proper file
def write_new_access(user,tok,_date):
   f = open(ACCESS_FILE,"a+")
   f.write(tok + "|" + _date + "\r\n")
   f.close()



# CREATE TEMPORARY TOKEN
def create_token():
 
   # Expired in one hour
   expiration = datetime.now() + timedelta(hours=1)
   
   # Create Token
   tok = expiration.strftime("%d%b%Y%H%M%S_4llsk")  + ''.join(random.choice('AbcDeFghIJklmNOpqRstUVWxYZ?_!') for _ in range(18))
   return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),tok


# TEST API LOGIN  
def test_api_login(tok):

   access_log_modified = False
   
   # Do the access file exists?
   if(os.path.isfile(ACCESS_FILE) == False):
      return False

   # Open the corresponding file
   with open(ACCESS_FILE) as f:
    lines = [line.rstrip() for line in f]
   
   for line in lines:
      tmp = line.split('|') 

      # Test the tok
      if(tok==tmp[0]):
         # We need to check the date
         valid_date = datetimestrptime(tmp[1],  "%a, %d-%b-%Y %H:%M:%S GMT")
         
         # Is date ok?
         now = datetime.now() 

         if(now>=valid_date):
            return False
         else:
            return True
         
 
        

   

   