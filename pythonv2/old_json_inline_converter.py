import os
import glob
import sys

from lib.Old_JSON_converter import convert, move_old_detection_to_archive


# Convert an old detection by updating the JSON and moving the file to /meteor_archive/
json_file = sys.argv[1]
video_file = sys.argv[2]
move_old_detection_to_archive(json_file,video_file,True)