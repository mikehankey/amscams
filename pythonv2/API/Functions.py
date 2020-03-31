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
JSON_MANAGER_PWD = '/home/ams/amscams/pythonv2/API/manager_password.json' 
API_TASK_FILE ='/home/ams/amscams/pythonv2/API/tasks.json' 
PATH_ACCESS_LOGS = '/home/ams/amscams/pythonv2/API'
ACCESS_FILE = PATH_ACCESS_LOGS + os.sep + "access.log"

DETECTION_TO_DEL = PATH_ACCESS_LOGS + os.sep + "toDel.log" 
DETECTION_TO_CONF = PATH_ACCESS_LOGS + os.sep + "toConf.log" 


EXTRA_CODE_IN_TOKEN = '4llskYR0cks'
ACCESS_GRANTED_DURATION = 1 # In hours

AUTHORIZED_FUNCTIONS = ['login','tasks','delete','confirm','update_frames']

# MAIN API CONTROLLER
def api_controller(form):
   cgitb.enable()

   api_function = form.getvalue('function')
   tok = form.getvalue('tok') 
   st = form.getvalue('st')
   user = form.getvalue('usr')

   # TEST API FUNCTION
   if(api_function is None):
      send_error_message('No API function found')
   elif(api_function not in AUTHORIZED_FUNCTIONS):
      send_error_message(api_function + ' is not an API function.')   

   # Login
   if(api_function=='login'):
      print(API_login(form))
   else:

      if(tok is None):
         send_error_message('Tok is missing')         

      # For everything else, we need to have a token passed 
      test_access = test_api_login(st,tok,user)
   
      if(test_access==False or test_access is None):
         send_error_message('You are not authorized. Please, try to logback in.',True)
      
      # Now we can do stuff
      if(api_function=='delete'):
         # Doesnt work yet
         print(delete_detection(form))

      # Update Frames for a given detection
      elif(api_function=='update_frames'):
 
         frames_data  = form.getvalue('data')
         print(add_frame_task(frames_data,user,st,datetime.now()))

      # Conf or Delete Detection(s)
      elif(api_function=='tasks'):
         data_to_del  = form.getvalue('data[toDel]')
         data_to_conf = form.getvalue('data[toConf]')

         if(data_to_del is None and data_to_conf is None):
            send_error_message('Data is missing - Error 145.hg')
         else:
            print(add_tasks(data_to_del,data_to_conf,user,st,datetime.now()))




# ADD TASK FOR NEW METEOR POS IN FRAMES
def add_frame_task(frame_data,usr,st,_date):

   with open(API_TASK_FILE, 'a+') as f:
      f.write(usr+'|'+st+'|FRAME'+'|'+frame_data+'|'+_date.strftime("%Y-%m-%d %H:%M")+'\n')

   f.close()       

   msg = '<b>A new task is now pending:</b><br/>Frames Updates'

 
   return json.dumps({'msg': msg})


# ADD A TASK TO DELETE A DETECTION that will be read later by a cron
# This function is used on the daily report + obs_report 
# to delete and/or confirm several detections 
def add_tasks(data_to_del,data_to_conf,usr,st,_date):
   
   # We can pass either strings or arrays
   if( isinstance(data_to_del, str)):
      all_data_to_del =  data_to_del 
 
   # We can pass either strings or arrays
   if( isinstance(data_to_conf, str)):
      all_data_to_conf =  data_to_conf

   conf_ct = 0
   del_ct = 0 

   try:
      all_data_to_del = data_to_del.split(',')
      del_ct = len(all_data_to_del)
   except:
      all_data_to_del = []

   try:
      all_data_to_conf = data_to_conf.split(',')
      conf_ct = len(all_data_to_conf)
   except:
      all_data_to_conf = []   
       

   #print("ADD TASKS")
   #print(all_data_to_del) 
   #print(all_data_to_conf)

   with open(API_TASK_FILE, 'a+') as f:
 
      for data in all_data_to_del:
         f.write(usr+'|'+st+'|DELETE'+'|'+data+'|'+_date.strftime("%Y-%m-%d %H:%M")+'\n')

      for data in all_data_to_conf:
         f.write(usr+'|'+st+'|CONF'+'|'+data+'|'+_date.strftime("%Y-%m-%d %H:%M")+'\n')

   f.close()

   # Build message for JS
   if(del_ct>1 or conf_ct>1):
      msg = '<b>New tasks are now pending:</b><br/>'
   else:
      msg = '<b>A new task is now pending:</b><br/>'

   if(del_ct!=0):
      msg += " deletion of " + str(del_ct) + " detection "
      if(conf_ct != 0) :
         msg += "and "
   if(conf_ct != 0) :
      msg += " confirmation of " + str(conf_ct) + " detection "


   return json.dumps({'msg': msg})


# LOGIN
def API_login(form):

   cgitb.enable() 

   station = form.getvalue('st')
   user = form.getvalue('usr') 
   password = form.getvalue('pwd')
   test_log = False 

   if(user is not None and password is not None and station is not None):

      pwd_file = JSON_USER_PWD
 
      user = user.strip() 
 
      json_file = open(pwd_file)
      json_str = json_file.read()
      json_data = json.loads(json_str)
 
      # We search the right pwd/usr/st
      if('access' in json_data):
         for acc in json_data['access']: 
            #USER
            if(station is not None):
               if(acc['st']==station and acc['usr']==user and acc['pwd']==password):
                  test_log = True
                  break 
           ##MANAGER
           # elif(acc['usr']==user and acc['pwd']==password):
           #       test_log = True
           #       break 
      

      if(test_log is True):
         _date, tok = create_token() 

         # Add the token to the current list of available token
         write_new_access(user,tok,_date,station)

         # We clean the accesslog
         test_api_login(station,tok,user) 

         return json.dumps({'token':tok,'expire':_date})
      else:
         return send_error_message('You are not authorized')

   else:
         return send_error_message('You need send at least a username, a password and a station ID.')
 

# DELETE function
def delete_detection(form):
   
   user = form.getvalue('user') 
   station = form.getvalue('st')
   detect_id = form.getvalue('detect') 

   if(detect_id is None):
      send_error_message('detect (detection ID) is required')

   now = datetime.now()

   with open(API_TASK_FILE, 'a') as f:
    f.write(user+'|DELETE'+'|'+detect_id+'|'+now.strftime("%Y-%m-%d %H:%M")+'\n')
   
   f.close()

   return json.dumps({'msg':'Deletion task added'})


# Write new access in proper file
def write_new_access(user,tok,_date,st):
   f = open(ACCESS_FILE,"a+")
   f.write(tok + "|" + _date + "|" + st + "|" + user +"\r\n")
   f.close()
 

# CREATE TEMPORARY TOKEN
def create_token():
 
   # Expired in one hour
   expiration = datetime.now() + timedelta(hours=ACCESS_GRANTED_DURATION)
   
   # Create Token
   tok = expiration.strftime("%d%b%Y%H%M%S"+EXTRA_CODE_IN_TOKEN)  + ''.join(random.choice('AbcDeFghIJklmNOpqRstUVWxYZ?_!') for _ in range(18))
   return expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT"),tok


# TEST API LOGIN  (remove all the access that are tool old)
def test_api_login(st,tok,user):
    
   # Do the access file exists?
   if(os.path.isfile(ACCESS_FILE) == False):
      return False

   # Open the corresponding file
   with open(ACCESS_FILE) as f:
    lines = [line.rstrip() for line in f]

   newlines = []
   ok = False
   t = False
   c = 0 

   for line in lines:
      tmp = line.split('|') 

      tok_to_test = tmp[0]
      time_to_test = tmp[1]
      station_to_test = tmp[2]
      user_to_test = tmp[3]
      
      # If we already have a valid token
      # we don't rewrite it on the access log
      if(tok == tok_to_test and user == user_to_test and st == station_to_test and ok is True):
         t = False 
      else:
         t = True
   
      # Test the tok
      if(t is True):

         # We need to check the date
         valid_date = datetime.strptime(time_to_test,  "%a, %d-%b-%Y %H:%M:%S GMT")
         
         # Is date ok?
         now = datetime.now() 
         
         # It hasn't expired!!  
         if(now<valid_date):
            newlines.append(line)
            ok = True 
 


   # Write the new lines in ACCESS_LOG
   with open(ACCESS_FILE, 'w') as outfile:
      for line in newlines:
         outfile.write(line + "\r\n")      

   return ok
 
 
        

   

   