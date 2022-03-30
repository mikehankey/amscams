import redis
import os
from datetime import datetime
import simplejson as json
import boto3
from lib.PipeUtil import load_json_file, save_json_file, cfe
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class UserReview():
   def __init__(self):
      self.dynamodb = boto3.resource('dynamodb')
      admin_conf = load_json_file("admin_conf.json")
      self.r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)

   def process_reviews_for_day(self,date,username=None):
      proc_log_dir = "/mnt/ams2/EVENTS/USER_REVIEWS/"
      if cfe(proc_log_dir,1) == 0:
         os.makedirs(proc_log_dir)
      proc_log_file = proc_log_dir + date + ".json"
      if cfe(proc_log_file) == 1:
         proc_log = load_json_file(proc_log_file)
      else:
         proc_log = {}
      admin_users = ['mhankey']
      station_perms = {}
      username = 'mhankey'
      print("Process user reviews for :", date)
      table = self.dynamodb.Table('user_review')
      response = table.query(
         KeyConditionExpression='username=:username AND report_date=:date',
         ExpressionAttributeValues={
           ':username': username,
           ':date': date,
         }
      )
      for item in response['Items']:
         # handle deletes
         for obs_key in item['deletes']:
            el = obs_key.split("_")
            station_id = el[0]
            log_key = username + "_" + obs_key
            if log_key in proc_log:
               print("Done already.", log_key)
               continue
            else:
               proc_log[log_key] = 1
            sd_video_file = obs_key.replace(station_id + "_", "")
            if ".mp4" not in sd_video_file:
               sd_video_file += ".mp4"
            print(station_id, sd_video_file, item['deletes'][obs_key])
            label = item['deletes'][obs_key]
            if username in admin_users:
               perms = "RW"
            elif username in station_perms:
               perms = "RW"
            else:
               perms = "R"

            print("DEL OBS:", username, station_id, sd_video_file, perms, label)
            self.del_obs(username, station_id, sd_video_file, perms, label)
      save_json_file(proc_log_file, proc_log)
   def del_obs(self,username, station_id, sd_video_file, perms, label):
        if ".mp4" not in sd_video_file:
           sd_video_file += ".mp4"
        if perms == "R":
            print("THIS USER DOES NOT HAVE RW PERMS!")
            rkey = "MRD:" + station_id + ":" + sd_video_file
            redis_review_data = self.r.get(rkey)
            print(redis_review_data)
            if redis_review_data is None:
              # No review exists yet. 
        
                payload = {}
                payload['station_id'] = station_id 
                payload['sd_video_file'] = sd_video_file
                payload['users'] = []
                payload['labels'] = []
                payload['submit_dates'] = []
                payload['users'].append(username ) 
                payload['labels'].append(label) 
                payload['submit_dates'].append(datetime.now().strftime("%Y_%m_%d_%H_%M_%S") )

                review_status = 0
                rpayload = json.dumps(payload,
                    cls=DecimalEncoder)
                self.r.set(rkey, rpayload)
                print("SET RED")
            else:
                payload = json.loads(redis_review_data)
                if username not in payload['users']:
                    payload['users'].append(username)
                    payload['reclass'].append(label)
                    payload['submit_dates'].append(datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
                    payload = json.dumps(payload,
                        cls=DecimalEncoder)
                    self.r.set(rkey, payload)
                    print("UDPATED RED")
            
            # insert community delete
            table = self.dynamodb.Table("meteor_review_delete")
            #Item =  json.loads(json.dumps(payload), parse_float=Decimal)
            Item = payload
            print("ITEM:", Item)
            table.put_item(Item=Item)
                    
            resp = {
                "statusCode": 200,
                "body": perms + " " + perms + " meteor delete logged"
            }
            return(resp)

        # Here are the DEL commands for RW users ONLY!
        # Do redis first
        rkey = "DM:" + station_id + ":" + sd_video_file
        ro_key = "O:" + station_id + ":" + sd_video_file
        roi_key = "OI:" + station_id + ":" + sd_video_file
        red_resp = self.r.delete(ro_key)
        red_resp = self.r.delete(roi_key)
        
        red_val = {"user": username}
        red_val = json.dumps(red_val,
                cls=DecimalEncoder)
        red_resp = self.r.set(rkey,red_val)
        # insert into del_obs table of the database
        
        Item = {
           "station_id": station_id,
           "sd_video_file" : sd_video_file,
           "user": username,
           "label": label,
           "delete_committed": 0
        }
        #Item =  json.loads(json.dumps(Item), parse_float=Decimal)
        
        table = self.dynamodb.Table("meteor_delete")
        print("ITEM2:", Item)
        table.put_item(Item=Item)
        
        mtable = self.dynamodb.Table("meteor_obs")
        mtable.update_item(
        Key = {
         'station_id':  station_id,
         'sd_video_file':  sd_video_file
        },
        UpdateExpression="set deleted = :deleted ",
        ExpressionAttributeValues={
         ':deleted': 1
        }
        )
        
        
        resp = {
          "statusCode": 200,
          "body": perms + " " + " meteor delete logged"
    
        }
        return(resp)
