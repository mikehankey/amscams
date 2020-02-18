import cgitb


MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step1.html"


# FIRST STEP: WE DEFINE THE ROI
def define_ROI(form):

   # Get stack
   stack = form.getvalue('stack')

   # Build the page based on template  
   with open(MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # We dont have any other info for the page
   template = template.replace("{HD_VIDEO}", "")
   template = template.replace("{SD_VIDEO}", "")
   template = template.replace("{JSON_FILE}","")
   

   # Display Template
   print(template) 
