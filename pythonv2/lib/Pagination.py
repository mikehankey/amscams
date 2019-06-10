import math
#import cgitb

def get_pagination(page,total_elts,url,max_per_page):
   

   #print("IN PAGINATION")
   #print("PAGE " +  format(page))
   #print("TOTAL ELTS " + format(total_elts))
   #print("URL " + url)
   #print("MAX PER P " + format(max_per_page))


   #cgitb.enable()

   # No Pagination Needed: return empty array
   if(total_elts <= max_per_page):
      return ["","",""]
 
   #how many pages appear to the left and right of your current page
   adjacents = 2

   start = (page - 1) * max_per_page; 
   display_page_counter = 0
   
   last_page = total_elts / max_per_page
   last_page = math.ceil(last_page)
   last_page = int(last_page) 
 
   #print("PAGE (cur): " + format(page))
   #print("TOTAL ELTS " + format(total_elts))
   #print("START: " + format(start))
   #print("LAST PAGE : " + format(last_page))
   
   lpm1 = last_page - 1
   _prev = page - 1
   _next = page + 1   

   pagination = '<nav class="mt-3">'

   if(last_page>1):

      pagination = pagination + "<ul class='pagination justify-content-center'>"

      #previous button
      if (page > 1):
         pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(_prev) +"'>&laquo; Previous</a></li>";
      else:
         # no Page "0"
         pagination = pagination + "<li class='page-item disabled'><a class='page-link' >&laquo; Previous</a></li>";

      display_page_counter = display_page_counter + 1

      #pages
      if (last_page < 5 + (adjacents * 2)):
      
         for counter in range(1,last_page+1):
            if(counter == page ):
               pagination = pagination + "<li class='page-item active'><a class='page-link' >"+ format(counter)+"</a></li>";
            else:
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(counter)+"'>"+format(counter)+"</a></li>";
            display_page_counter = display_page_counter + 1
            
      elif (last_page > 5 + (adjacents * 2)):

         #close to beginning; only hide later pages
         if(page < 3 + (adjacents * 2)):
               
               for counter in range(1,4 + (adjacents * 2)):
                  if(counter == page):
                     pagination = pagination + "<li class='page-item active'><a class='page-link' >"+format(counter)+"</a></li>";
                  else:
                     pagination = pagination + "<li class='page-item'><a class='page-link'  href='"+url+"&p="+ format(counter)+"'>"+ format(counter)+"</a></li>";
                  display_page_counter = display_page_counter + 1

               pagination = pagination + "<li class='page-item disabled'><a class='page-link'>...</a></li>";
               pagination = pagination + "<li class='page-item'><a  class='page-link' href='"+url+"&p=" + format(lpm1)+"'>"+format(lpm1)+"</a></li>";
               pagination = pagination + "<li class='page-item'><a  class='page-link' href='"+url+"&p=" + format(last_page)+"'>"+ format(last_page)+"</a></li>";
               display_page_counter = display_page_counter + 2

         elif(last_page-1-(adjacents*2)>page and page > (adjacents*2)):

               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=1'>1</a></li>";
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=2'>2</a></li>";
               pagination = pagination + "<li class='disabled page-item'><a class='page-link'>...</a></li>";

               display_page_counter = display_page_counter + 2
               
               for counter in range(page-adjacents, page+adjacents):
                  if(counter == page):
                     pagination = pagination + "<li class='page-item active'><a class='page-link' >"+format(counter)+"</a></li>";                   
                  else:
                     pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p="+ format(counter)+"'>"+format(counter)+"</a></li>";
                  display_page_counter = display_page_counter + 1
               
               pagination = pagination + "<li class='page-item disabled'><a class='page-link'>...</a></li>";
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(lpm1)+"'>"+format(lpm1)+"</a></li>";
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(last_page)+"'>"+format(last_page)+"</a></li>";
               display_page_counter = display_page_counter + 2

         #close to end; only hide early pages
         else:
               
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=1'>1</a></li>";
               pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=2'>2</a></li>";
               pagination = pagination + "<li class='disabled page-item'><a class='page-link'>...</a></li>";
               display_page_counter = display_page_counter + 2

               for counter in range(last_page - (2 + (adjacents * 2)), last_page):
                  if(counter == page):
                     pagination = pagination + "<li class='page-item active'><a class='page-link'>"+format(counter)+"</a></li>";                   
                  else:
                     pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p="+ format(counter)+"'>"+format(counter)+"</a></li>";
                  display_page_counter = display_page_counter + 1

   else:
      #Display all pages
      for counter in range(1,last_page):
         if(counter == page):
            pagination = pagination + "<li class='page-item active'><a class='page-link' >"+format(counter)+"</a></li>";
         else:
            pagination = pagination + "<li class='page-item active'><a class='page-link' href='"+url+"&p=" + format(counter)+"' >"+format(counter)+"</a></li>";
 
         display_page_counter = display_page_counter + 2


   if (page < display_page_counter and page + 1 < last_page):
      pagination =  pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(page+1)+"'>Next &raquo;</a></li>"
   else:
      pagination =  pagination + "<li class='page-item disabled'><a class='page-link'>Next &raquo;</a></li>"


   to_return  = [pagination, start, last_page]

   return(to_return)