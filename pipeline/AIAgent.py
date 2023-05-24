from prettytable import PrettyTable as pt
import daemon
import datetime as dt
from datetime import datetime
import os
import time
from Classes.AIAgent import AIAgent

from lib.PipeUtil import check_running, load_json_file, save_json_file

import logging
logging.basicConfig(filename='AIAgent.log')
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

"""

The AIAgent will take over as the primary task manager for ASOS tasks, ultimately replacing the run_jobs scripts.

The AIAgent will also handle batch / cleanup type of jobs that must run on all meteors in the archive.

For now, slowly we will take over these batch jobs :
   Batch Jobs
      1) AI Scan for past days 
      2) myEvents for past days 
      3) Sync AWS Deletes past days
      4) Past weather

      A "job" object looks like this in the run-jobs.json: 
      {
         "name": "hour_stacks_yesterday",
         "desc": "Make the hour stacks for yesterday.",
         "home_dir": "amscams/pipeline/",
         "exe": "./Process.py hs {yesterday}",
         "job_type": "stacking",
         "interval": "hour",
         "frequency": 3,
         "priortiy": 1,
         "notes": "# make all hourly stacks for yesterday"
      },

"""

def job_report(run_job_data):
    tb = pt()
    tb.field_names = ["Job Name","Type","Exe", "Frequency", "Last Run"] #,"Last Run", "Run In " ]
    now = datetime.now()
    now_date_str =  now.strftime("%Y_%m_%d %H:%M:%S")

    logger.debug("DEBUG: Running job report @ " + now_date_str)
    #logger.warning("WARNING: Running job report.")
    #logger.info("INFO: Running job report.")
    #input("YO")

    job_intervals = run_job_data['job_intervals']
    job_types = run_job_data['job_types']
    job_list = run_job_data['job_list']

    report = {}
    updated_job_list = []
    for jt in job_types:
       report[jt] = {}
    for row in job_list:

       if "interval" in row:
          interval = row['interval']
       else:
          interval = "HOUR"
       if "frequency" in row:
          frequency = row['frequency']
       else:
          frequency = 8




       if "job_type" in row:
          jt = row['job_type']
       else:
          jt = None
       if "last_run" in row:
          last_run = row['last_run']
       else:
          # never
          last_run = "NEVER"
          row['last_run'] = last_run

       jname = row['name']
       exe = row['exe']
       if jt is not None:
          report[jt] = {}
          report[jt][jname] = {}
       print(jt, jname, exe)
       tb.add_row([jname,jt,exe,str(frequency) + " " + interval, last_run])
       updated_job_list.append(row)
    print(tb)

    run_job_data['job_list'] = updated_job_list
    return(run_job_data)
    #print(report)   

def ai_task_manager(AIA):
    # this program will loop over all of the "jobs" and things that must be managed
    # it will track the last time something was done and the status of completion 
    # and report back as needed or do things as needed 
    json_conf = load_json_file("../conf/as6.json")
    job_index = {}
    station_job_index = {}
    run_jobs_station_file = "run_jobs_" + json_conf['site']['ams_id'] +".json"

    # load stock job data 
    run_jobs_stock_data = load_json_file("run_jobs.json")
    for row in run_jobs_stock_data['job_list']:
       print("ROW", row)
       name = row['name']
       if name not in job_index:
          job_index[name] = row
   
    # load station job data 
    if os.path.exists(run_jobs_station_file) is True:
       run_jobs_station_data = load_json_file(run_jobs_station_file)
       run_jobs_station_data_updated = []
       # remove invalid jobs
       for row in run_jobs_station_data['job_list']:
          name = row['name'] 
          if name in job_index: 
             run_jobs_station_data_updated.append(row)
             station_job_index[name] = row
          else:
             # job no longer valid
             print("Skip / remove: Job no longer valid", ROW)
       # add missing jobs 
       for row in run_jobs_stock_data['job_list']:
          name = row['name'] 
          if name in job_index and name not in station_job_index: 
             run_jobs_station_data_updated.append(row)
       run_jobs_station_data['job_list'] = run_jobs_station_data_updated
             
    else:
       run_jobs_station_data = run_jobs_stock_data 

    job_intervals = run_jobs_station_data['job_intervals']
    job_types = run_jobs_station_data['job_types']
    job_list = run_jobs_station_data['job_list']

    run_jobs_station_data = job_report(run_jobs_station_data)
    exit()

    last_run = {}
    while True:
        # the loop will run 1x per sleep interval below.
        # the idea here is to have a master list of jobs/frequencies and last run times
        # the re-run things as needed per the interval
        # this task manager should keep tabs on just about everything! 
        # it should be self healing, meaning it can fix things that are broken
        # or if it can't be fixed it should report an alert
        now = datetime.now()
        yest = now - dt.timedelta(days=1)
        today = datetime.now().strftime("%Y_%m_%d")
        yest = yest.strftime('%Y_%m_%d') 


        for obj in job_list:
            run_job = 0
            job_id = obj['name']
            job_freq = obj['frequency']
            job_interval = obj['interval']
            if job_interval == "hour":
                # make jobtime in seconds (run job every xxx seconds)
                job_time = job_freq * 60 * 60 

            if job_id not in last_run:
                last_run[job_id] = time.time()
                elp_time = 0 
                run_job = 1
            else:
                elp_time = time.time() - last_run[job_id]  
                if elp_time > job_time:
                    print("TIME ELAPSED JOB MUST BE RE-RUN!")
                    run_job = 1
                else:
                    print("Not enough time has passed. ", elp_time, job_time)

            if run_job == 1:
                cmd = "cd /home/ams/" + obj['home_dir'] + "; " + obj['exe']
                cmd = cmd.replace("{today}", today)
                cmd = cmd.replace("{yesterday}", yest)
                print("RUN JOB:", elp_time, obj['name'], cmd)
                logger.info(time.ctime() + ":" + cmd + "\n")
            else:
               time_left = int((job_time - elp_time) / 60)
               print("SKIP JOB", job_id, "Run in {} minutes".format(time_left))

        logger.info(time.ctime() + ":end of loop" + "\n")
        time.sleep(60)

def run(AIA):
    ai_task_manager(AIA)

    # run as a daemon
    if False:
        with daemon.DaemonContext():
            ai_task_manager(AIA)

if __name__ == "__main__":
    running = check_running("AIAgent.py")
    AIA = AIAgent()
    #AIA.index_archive_tasks()

    if running < 2:
       print("PROCESSES RUNNING:", running)
       run(AIA)
    else:
       print("AI Agent is already running.")
