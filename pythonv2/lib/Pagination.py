import math
import cgitb

def get_pagination(page,total_elts,url,max_per_page):

      links = 5 #Number of adjcents links

      if(max_per_page >= total_elts):
            return ["","",""]
      
      total_elts = float(total_elts) # to make sure we have the proper result
      
      #get the last page number
      last = math.ceil(total_elts/max_per_page)
      last = int(last)

      #calculate start of range for link printing
      if(page - links > 0):
            start = page - links
      else:
            start = 1
      
      #calculate end of range for link printing
      if(page + links < last):
            end = page + links
      else:
            end = last

     
      pagination = '<nav class="mt-3"><ul class="pagination justify-content-center">'

      if(page==1):
            pagination = pagination + "<li class='page-item disabled'><a class='page-link' >&laquo; Previous</a></li>";
      else:
            pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(page-1)+"'>&laquo; Previous</a></li>";
      
      
      if(start>1):
            pagination = pagination + "<li class='page-item'><a href='"+url+"&p=1' class='page-link'>1</a></li>";
            pagination = pagination + "<li class='page-item disabled'><a class='page-link'><span>&hellip;</span></a></li>";

      #Print All other pages
      for counter in range(start,end+1):
            if(counter == page):
                  pagination = pagination + "<li class='page-item active'><a class='page-link' href='"+url+"&p=" + format(counter)+"'>"+format(counter)+"</a></li>";
            else:
                  pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(counter)+"'>"+format(counter)+"</a></li>";

      if(end < last):
            pagination = pagination + "<li class='page-item disabled'><a class='page-link'><span>&hellip;</span></a></li>";            
            pagination = pagination + "<li class='page-item '><a href='"+url+"&p="+format(last)+"' class='page-link'>"+format(last)+"</a></li>";

      if(page == last):
            pagination = pagination + "<li class='page-item disabled'><a class='page-link' >Next &raquo;</a></li>";
      else:
            pagination = pagination + "<li class='page-item'><a class='page-link' href='"+url+"&p=" + format(page+1)+"'>Next &raquo;</a></li>";

      pagination = pagination +  "</ul></nav>"

      to_return  = [pagination, start, last]

      return(to_return)