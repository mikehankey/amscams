#!/usr/bin/python3



def check_running():
   cmd = "/sbin/ifconfig -a | grep 10.8.0 | grep -v grep | wc -l"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   print(output)
   return(int(output))

# check if flask admin is enabled and make sure it is runnniing if it is
if "flask_admin" in json_conf:
   cmd = "ps -aux |grep \"wsgi\" | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   flask_running = int(output.replace("\n", ""))
   if flask_running == 0:
      print("FLASK RUNNING:", flask_running)
      cmd = "cd /home/ams/amscams/pipeline; /home/ams/amscams/pipeline/run-uwsgi.sh > /tmp/sgi.txt 2>&1 & "
      print(cmd)
      os.system(cmd)

