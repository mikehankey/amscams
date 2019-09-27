import os
import glob
import sys

from lib.Old_JSON_conveter import convert, move_old_to_archive


json_file = sys.argv[1]
#convert(json_file)
move_old_to_archive(json_file)