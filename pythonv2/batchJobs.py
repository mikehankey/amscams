#!/usr/bin/python3

from lib.BatchLib import batch_thumb, make_file_index
from lib.FileIO import load_json_file
import sys

json_conf = load_json_file("../conf/as6.json")

if sys.argv[1] == 'bt':
   batch_thumb(json_conf)
if sys.argv[1] == 'mi':
   make_file_index(json_conf)
