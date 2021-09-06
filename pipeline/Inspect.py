from Classes.EventInspect import EventInspect

import sys

I = EventInspect()
I.data = {}
I.data['event_id'] = sys.argv[1]
I.event_inspect()
