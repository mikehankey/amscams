from Classes.ReviewNetwork import ReviewNetwork
import sys

date = sys.argv[1]
RN = ReviewNetwork()
RN.review_meteors(date)

