from Classes.AllSkyNetwork import AllSkyNetwork

import sys

cmd = sys.argv[1]

ASN = AllSkyNetwork()
if len(sys.argv) < 1:
   ASN.help()
   exit()

if cmd == "resolve_event":
   ASN.resolve_event(sys.argv[2])

if cmd == "day_load_solve_results":
   ASN.day_load_solve_results(sys.argv[2])

if cmd == "day_load_sql":
   if len(sys.argv) == 4:
      force = 1
   else:
      force = 0
   ASN.day_load_sql(sys.argv[2], force)
   ASN.day_coin_events(sys.argv[2],force)
   ASN.day_solve(sys.argv[2],force)

if cmd == "status":
   if len(sys.argv) < 2:
      print("No date provided!")
      print("USAGE: ./AllSkyNetwork status [YYYY_MM_DD]")

   ASN.day_status(sys.argv[2])
