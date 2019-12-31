import datetime
import sys

from lib.Archive_Listing import get_index 
from lib.FileIO import load_json_file

def get_stats_from_year_index(year):
   json_data =  get_index(year)
    
   print("YEAR " + json_data['year'] + "<br/>")
   print("STATION ID " + json_data['station_id'] + "<br/>")
   for month in json_data['months']:
      print(month)
      print("<br/>")
   

# MAIN FUNCTION FOR THE STATS PAGE
def stats_page(form): 
   year = form.getvalue('year')

   if(year is None):
      now = datetime.datetime.now() 
      year = now.year

   res = get_stats_from_year_index(year)
 