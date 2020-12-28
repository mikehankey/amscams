#!/usr/bin/python3

import sys
import os

from lib.PipeSolve import simple_solve
from lib.PipeUtil import load_json_file 

json_conf = load_json_file("../conf/as6.json")

cmd = sys.argv[1]
if cmd == 'ss':
   day = sys.argv[2]
   event_id = sys.argv[3]
   simple_solve(day, event_id,json_conf)
