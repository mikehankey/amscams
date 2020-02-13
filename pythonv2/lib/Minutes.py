import glob
import re
import cgitb

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/browse_minutes.html"


def browse_minute(form):
   # Debug
   cgitb.enable()

   period   = form.getvalue('period')
   cams_ids = form.getvalue('cams_ids')

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()
   
   # Display Template
   print(template)

