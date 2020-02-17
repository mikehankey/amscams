import cgitb
 
from lib.Minutes_Tools import *

PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/minute_details.html"

def minute_details(form):
   # Debug
   cgitb.enable()
   stack = form.getvalue('stack') 

   analysed_minute = minute_name_analyser(stack)
   
    # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()


   print(template)
   print(analysed_minute)

