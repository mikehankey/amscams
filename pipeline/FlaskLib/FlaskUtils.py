def get_template(file): 
   out = ""
   fp = open(file, "r")
   for line in fp:
      out += line
   fp.close()
   return(out)


