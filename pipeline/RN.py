from Classes.ReviewNetwork import ReviewNetwork
import sys

cmd = sys.argv[1]
date = sys.argv[2]
RN = ReviewNetwork(date)
if cmd == "RN":
   RN.review_meteors(date)
if cmd == "RE" or cmd == "re" or cmd == "review_events":
   RN.review_events(date)
#RN.review_event_meteors(date)

