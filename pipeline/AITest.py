from Classes.ASAI import AllSkyAI 
from datetime import datetime
import datetime as dt
import sys
import os

ASAI = AllSkyAI()

roi_file = "/mnt/ams2/METEOR_SCAN/2022_02_01/AMS1_2022_02_01_01_22_00_000_010001-trim-0230-ROI.jpg"
root_fn = "AMS1_2022_02_01_01_22_00_000_010001-trim-0230-ROI.jpg"
oimg = None
roi = None

result = ASAI.meteor_yn(root_fn,roi_file,oimg,roi)
print(result)
