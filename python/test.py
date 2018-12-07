
import ephem
import json
import subprocess
import glob
import time
import datetime
import os

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)

