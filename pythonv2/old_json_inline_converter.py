import os
import glob
import sys

from lib.Old_JSON_conveter import convert


json_file = sys.argv[1]
convert(json_file)
