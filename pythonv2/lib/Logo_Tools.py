import os
import uuid
import shutil
from lib.LOGOS_VARS import LOGOS_PATH 

def upload_logo(form):
    logo = form.getvalue("logo")
 
    fileitem = logo
    if fileitem.file:
        # It's an uploaded file; count lines
        linecount = 0
        while 1:
            line = fileitem.file.readline()
            if not line: break
            linecount = linecount + 1
        
        print("linecount " + linecount)
        print(fileitem.file)
    else:
        print("NO FILE FOUND")