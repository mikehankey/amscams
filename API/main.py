import os
import cgi
print ("Content-type: text/html\n\n")

def api_controller(form):
   api_function = form.getvalue('function')

   if(api_function=='login'):
      login(form)

def login(form):

   user = form.getvalue('user')
   password = form.getvalue('pwd')

   print("RIGHT")


form = cgi.FieldStorage()
api_controller(form)
