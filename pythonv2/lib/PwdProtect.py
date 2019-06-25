import datetime
import random
import cgitb

def setup_pwd(domain,user,pwd):
    cgitb.enable()
    expiration = datetime.datetime.now() + datetime.timedelta(days=0.5)
    print ("Set-Cookie:User = "+user+";\r\n")
    print ("Set-Cookie:Password = "+pwd+"";\r\n")
    print ("Set-Cookie:Expires = "+expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT")+";\r\n")
    print ("Set-Cookie:Domain = lovable-falcon-4326.dataplicity.io;\r\n")
    print ("Set-Cookie:Path = /;\n")
    print ("Content-type:text/html\r\n\r\n")

  
    
    #print "Set-Cookie:UserID = XYZ;\r\n"
    #print "Set-Cookie:Password = XYZ123;\r\n"
    #print "Set-Cookie:Expires = Tuesday, 31-Dec-2007 23:12:40 GMT";\r\n"
    #print "Set-Cookie:Domain = www.tutorialspoint.com;\r\n"
    #print "Set-Cookie:Path = /perl;\n"
    #print "Content-type:text/html\r\n\r\n"