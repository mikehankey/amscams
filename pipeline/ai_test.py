from Classes.ASAI import AllSkyAI
from datetime import datetime
import datetime as dt
import sys
import os

ASAI = AllSkyAI()
ASAI.load_all_models()

roi_file = "/mnt/ams2/METEOR_SCAN/2022_02_01/AMS1_2022_02_01_01_22_00_000_010001-trim-0230-ROI.jpg"
roi_file = "/mnt/ams2/METEOR_SCAN/2022_02_26/AMS1_2022_02_26_06_33_01_000_010005-trim-0260-ROI.jpg"
root_fn = roi_file.split("/")[-1]
oimg = None
roi = None

result = ASAI.meteor_yn(root_fn,roi_file,oimg,roi)
print(result)

