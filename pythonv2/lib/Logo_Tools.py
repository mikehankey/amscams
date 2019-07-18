import os
import uuid
import shutil
import cgitb
from lib.LOGOS_VARS import LOGOS_PATH 

def upload_logo(form):
    cgitb.enable()
    logo = form.getvalue("logo")
    fileitem = logo
    print('FILE ITEM' + fileitem)
    print('FILE ITEM FILE' + fileitem.file)
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