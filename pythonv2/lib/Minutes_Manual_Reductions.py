import cgitb

from lib.Minutes_Tools import minute_name_analyser


MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/minute_manual_reduction_template_step0.html"

# FIRST STEP: WE DEFINE THE ROI
def define_ROI(form):

   # Get stack
   stack = form.getvalue('stack')

   # Build the page based on template  
   with open(MANUAL_RED_MINUTE_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # We dont have any other info for the page
   template = template.replace("{STACK}",stack) 
   

   # Display Template
   print(template) 


# SECOND STEP: GET HD 
def automatic_detect(form):
   
   # In form we should have
   stack = form.getvalue('stack')
   # ROI
   x = form.getvalue('x_start')
   y = form.getvalue('y_start')
   w = form.getvalue('w')
   h = form.getvalue('h')


   # Do we have a HD version on the video of this stack?
   # Ex: 
   # stack = /mnt/ams2/SD/proc2/2020_02_17/images/2020_02_17_11_19_47_000_010037-stacked-tn_HD_tmp_stack.png
   # video => /mnt/ams2/SD/proc2/2020_02_17/2020_02_17_11_19_47_000_010037.mp4
   analysed_minute = minute_name_analyser(stack)
   print(analysed_minute)



