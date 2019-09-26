import sys

# CGI redirect
def redirect_to(redirectURL):
   print( '<html  style="width:100vw; height:100vh; background:#000">')
   print( '  <head>')
   print( '    <meta http-equiv="refresh" content="0;url='+redirectURL+'" />' )
   print( '    <title>You are going to be redirected</title>')
   print( '  </head>') 
   print( '  <body style="width:100vw; height:100vh; background:#000">')
   print('<div style="color:#000; background:#000">')
   print( '    Redirecting... <a href="'+redirectURL+'" style="color:#000">Click here if you are not redirected</a>')
   print('</div'); 
   print( '  </body>')
   print( '</html>')
   sys.exit(0)