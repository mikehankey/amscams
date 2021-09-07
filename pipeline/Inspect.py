from Classes.EventInspect import EventInspect

import sys
event_id = sys.argv[1]

if sys.argv[1] == "merge":
   I = EventInspect(sys.argv[2])
   I.make_final_kml()
   exit()

I = EventInspect(event_id)
#I.data = {}
I.event_inspect()
I.make_final_kml()
