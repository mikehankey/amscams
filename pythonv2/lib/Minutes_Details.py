import cgitb

def minute_details(form):
   # Debug
   cgitb.enable()

   stack = form.getvalue('stack')  