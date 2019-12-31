import datetime
from lib.Archive_Listing import get_index 

def get_stats_from_year_index(year):
   json_index =  get_index(year)
   print("INDEX YEAR: ")
   print(json_index)

# MAIN FUNCTION FOR THE STATS PAGE
def stats_page(form): 
   year = form.getvalue('year')

   if(year is None):
      now = datetime.datetime.now() 
      year = now.year

   res = get_stats_from_year_index(year)
 