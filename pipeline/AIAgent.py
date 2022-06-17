import daemon
import datetime as dt
from datetime import datetime
import os
import time
from Classes.AIAgent import AIAgent

from lib.PipeUtil import check_running, load_json_file, save_json_file

"""

The AIAgent will take over as the primary task manager for ASOS tasks, ultimately replacing the run_jobs scripts.

The AIAgent will also handle batch / cleanup type of jobs that must run on all meteors in the archive.

For now, slowly we will take over these batch jobs :
   Batch Jobs
      1) AI Scan for past days 
      2) myEvents for past days 
      3) Sync AWS Deletes past days
      4) Past weather


"""

def ai_task_manager(AIA):
    run_job_data = load_json_file("run_jobs.json")
    job_list = run_job_data['job_list']
    log = open("/home/ams/ai_agent.log", "w") 
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
                log.write(time.ctime() + ":" + cmd + "\n")
            else:
               time_left = int((job_time - elp_time) / 60)
               print("SKIP JOB", job_id, "Run in {} minutes".format(time_left))

        log.write(time.ctime() + ":end of loop" + "\n")
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
    AIA.index_archive_tasks()

    if running < 2:
       print("PROCESSES RUNNING:", running)
       run(AIA)
    else:
       print("AI Agent is already running.")
