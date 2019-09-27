import os
import glob
import sys

from lib.Old_JSON_conveter import convert, move_old_to_archive


# Convert an old detection by updating the JSON and moving the file to /meteor_archive/
json_file = sys.argv[1]
move_old_to_archive(json_file,True)