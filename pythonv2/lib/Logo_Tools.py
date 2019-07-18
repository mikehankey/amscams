import os
import uuid
import shutil
from lib.LOGOS_VARS import LOGOS_PATH 

def upload_logo(form):
    logo = form.getvalue("logo").filename 
    print("TEST " + logo)