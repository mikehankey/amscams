import os

def controller(form):
   api_function = form.getvalue('function')

   if(api_function=='login'):
      login(form)

def login(form):

   user = form.getvalue('user')
   password = form.getvalue('pwd')

   print("RIGHT")
 
controller(json_conf)
 

