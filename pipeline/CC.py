import datetime
from decimal import Decimal
from Classes.CleanCal import CleanCal
import sys

# CLEAN CAL CLASS INTERFACE

if __name__ == "__main__":
   import sys
   cmd = sys.argv[1]

   CC = CleanCal(station_id = "AMS1")
   #CC.load_freecal_files()
   CC.load_freecal_index()
