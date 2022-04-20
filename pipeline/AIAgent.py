import daemon
import os
import time
from Classes.AIAgent import AIAgent

from lib.PipeUtil import check_running

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



    while True:
        with open("/tmp/current_time.txt", "w") as f:
            f.write("The time is now " + time.ctime())
        time.sleep(5)

def run(AIA):
    with daemon.DaemonContext():
        ai_task_manager(AIA)

if __name__ == "__main__":
    running = check_running("AIAgent.py")
    AIA = AIAgent()
    AIA.index_archive_tasks()
    for day in AIA.all_days:
       print(day, AIA.all_days[day])
       cmd = "python3.6 AIDay.py " + day
       os.system(cmd)
    exit()
    if running < 2:
       print("PROCESSES RUNNING:", running)
       run(AIA)
    else:
       print("AI Agent is already running.")
