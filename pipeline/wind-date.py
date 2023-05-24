import datetime
import sys
import time
obs_dt = datetime.datetime.strptime(sys.argv[1], "%Y_%m_%d")
ts = datetime.datetime.timestamp(obs_dt)
print(obs_dt, ts, ts+86400)

