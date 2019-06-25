import Cookie
import datetime
import random
import cgitb

def setupPwd(domain,user,pwd):
    cgitb.enable()
    expiration = datetime.datetime.now() + datetime.timedelta(days=0.5)
    ses = random.randint(0,1000000000)
    cookie = Cookie.SimpleCookie()
    cookie["session"] = ses
    cookie["session"]["domain"] = domain
    cookie["session"]["path"] = "/"
    cookie["session"]["expires"] = expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT")

    print "Content-type: text/plain"
    print cookie.output()
    print "Cookie set with: " + cookie.output()

    return cookie["session"]
    
    #print "Set-Cookie:UserID = XYZ;\r\n"
    #print "Set-Cookie:Password = XYZ123;\r\n"
    #print "Set-Cookie:Expires = Tuesday, 31-Dec-2007 23:12:40 GMT";\r\n"
    #print "Set-Cookie:Domain = www.tutorialspoint.com;\r\n"
    #print "Set-Cookie:Path = /perl;\n"
    #print "Content-type:text/html\r\n\r\n"