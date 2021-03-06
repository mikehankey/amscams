import os, os.path
import uuid
import shutil
import cgitb
from lib.LOGOS_VARS import LOGOS_PATH 

def upload_logo(form):
    #cgitb.enable()

    try:
        logo = form.getvalue("logo")
        
        #Is the LOGOS_PATH folder exists? 
        if not os.path.exists(LOGOS_PATH):
            os.makedirs(LOGOS_PATH)

        #Count the Existing Logos 
        cur = len([name for name in os.listdir(LOGOS_PATH) if os.path.isfile(os.path.join(LOGOS_PATH, name))])
        cur += 1

        #print("WE CURRENTLY HAVE " + str(cur) + " LOGOS")

        #Create PNG in LOGOS_PATH
        f= open(LOGOS_PATH+str(cur)+'.png',"wb+")
        f.write(bytes(logo))
        f.close()
    
        print("{'msg':'Logo Uploaded'}")
    except:
        print("{'error':'Something went wrong, please try again'}")

    #print("LOGO SHOULD BE HERE: " + LOGOS_PATH+str(cur)+'.png')
