#!/usr/bin/python3

import os
import cgi 
import sys
import cgitb
import string
import random
import json 
 
from datetime import datetime, timedelta
from os import environ 

from API_Tools import *
from API_Functions import *

JSON_USER_PWD = '/home/ams/amscams/pythonv2/API/user_password.json' 
JSON_MANAGER_PWD = '/home/ams/amscams/pythonv2/APImanager_password.json' 
PATH_ACCESS_LOGS = '/home/ams/amscams/pythonv2/API'
ACCESS_FILE = PATH_ACCESS_LOGS + os.sep + "access.log"
EXTRA_CODE_IN_TOKEN = '4llskYR0cks'
ACCESS_GRANTED_DURATION = 1 # In hours

AUTHORIZED_FUNCTIONS = ['login','delete']

# MAIN API CONTROLLER
def api_controller(form):
   cgitb.enable()

   api_function = form.getvalue('function')
   tok = form.getvalue('tok') 

   # TEST API FUNCTION
   if(api_function is None):
      send_error_message('No API function found')
   elif(api_function not in AUTHORIZED_FUNCTIONS):
      send_error_message(api_function + 'is not an API function.')   

   # Login
   if(api_function=='login'):
      print(API_login(form))
   else:

      if(tok is None):
         send_error_message('Tok is missing')         

      # For everything else, we need to have a token passed
      test_access = test_api_login(tok)
   
      if(test_access==False or test_access is None):
         send_error_message('You are not authorized')
      
      # Now we can do stuff
      if(api_function=='delete'):
         delete_detection(form)


# LOGIN
def API_login(form):

   cgitb.enable() 

   station = form.getvalue('st')
   user = form.getvalue('user') 
   password = form.getvalue('pwd')
   test_log = False

   if(user is not None and password is not None):

      # The 'users' have to pick a station
      # while the manager are required to...
      if(station is not None):
         pwd_file = JSON_USER_PWD
      else:
         pwd_file = JSON_MANAGER_PWD
 
      user = user.strip() 
 
      json_file = open(pwd_file)
      json_str = json_file.read()
      json_data = json.loads(json_str)
 
      # We search the right pwd/usr/st
      if('access' in json_data):
         for acc in json_data['access']: 
            if(station is not None):
               print("STATION NOT NONE<br/>")
               print("TEST<br/>")
               print(acc)
               if(acc['st']==station and acc['usr']==user and acc['pwd']==password):
                  text_log = True
                  break 
            elif(acc['usr']==user and acc['pwd']==password):
                  text_log = True
                  break 


      if(test_log is True):
         _date, tok = create_token() 

         # Add the token to the current list of available token
         write_new_access(user,tok,_date)

         return json.dumps({'token':tok,'expire':_date})
      else:
         return send_error_message('You are not authorized')

   else:
         return send_error_message('You need send at least a username and a password (and a station ID if you are not a manager ).')
 



# Write new access in proper file
def write_new_access(user,tok,_date):
   f = open(ACCESS_FILE,"a+")
   f.write(tok + "|" + _date + "\r\n")
   f.close()



# CREATE TEMPORARY TOKEN
def create_token():
 
   # Expired in one hour
   expiration = datetime.now() + timedelta(hours=ACCESS_GRANTED_DURATION)
   
   # Create Token
   tok = expiration.strftime("%d%b%Y%H%M%S"+EXTRA_CODE_IN_TOKEN)  + ''.join(random.choice('AbcDeFghIJklmNOpqRstUVWxYZ?_!') for _ in range(18))
   return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),tok


# TEST API LOGIN  (remove all the access that are tool old)
def test_api_login(tok):
    
   # Do the access file exists?
   if(os.path.isfile(ACCESS_FILE) == False):
      return False

   # Open the corresponding file
   with open(ACCESS_FILE) as f:
    lines = [line.rstrip() for line in f]

   newlines = []
   ok = False
   
   for line in lines:
      tmp = line.split('|') 

      if(EXTRA_CODE_IN_TOKEN in tmp[0]):
         tok_to_test = tmp[0]
         time_to_test = tmp[1]
      else:
         time_to_test = tmp[0]
         tok_to_test = tmp[1] 

      # Test the tok
      if(tok==tok_to_test):

         # We need to check the date
         valid_date = datetime.strptime(time_to_test,  "%a, %d-%b-%Y %H:%M:%S GMT")
         
         # Is date ok?
         now = datetime.now() 
         
         # It hasn't expired!!  
         if(now<valid_date):
            newlines.append(line)
            ok = True
      else:
         # We need to check the date
         valid_date = datetime.strptime(time_to_test,  "%a, %d-%b-%Y %H:%M:%S GMT")

         # Is date ok?
         now = datetime.now() 

         if(now<valid_date):
            newlines.append(line)

   # Write the new lines in ACCESS_LOG
   with open(ACCESS_FILE, 'w') as outfile:
      for line in newlines:
         outfile.write(line + "\r\n")

   if(ok is True):
      return True

   return False
         
 
        

   

   