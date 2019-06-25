import datetime 
import cgitb
 

def login_page():
    cgitb.enable()
    template = ""
    fpt = open("/home/ams/amscams/pythonv2/templates/login.html", "r")
    for line in fpt:
        template = template + line
    print(template)

def setup_pwd(domain,user,pwd):

    #setup_pwd('www.moncul.com','toto','t0t0t')
    cgitb.enable()
    expiration = datetime.datetime.now() + datetime.timedelta(days=0.5)
    
    print("Content-type:text/html\r\n")
    print("Set-Cookie:User = "+user+";\r\n")
    print("Set-Cookie:Password = "+pwd+"\r\n")
    print("Set-Cookie:Expires = "+expiration.strftime("%a, %d-%b-%Y %H:%M:%S GMT")+";\r\n")
    print("Set-Cookie:Domain = lovable-falcon-4326.dataplicity.io;\r\n")
    print("Set-Cookie:Path = /;\n")
 
    
    #print "Set-Cookie:UserID = XYZ;\r\n"
    #print "Set-Cookie:Password = XYZ123;\r\n"
    #print "Set-Cookie:Expires = Tuesday, 31-Dec-2007 23:12:40 GMT";\r\n"
    #print "Set-Cookie:Domain = www.tutorialspoint.com;\r\n"
    #print "Set-Cookie:Path = /perl;\n"
    #print "Content-type:text/html\r\n\r\n"
