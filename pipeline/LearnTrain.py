#!/usr/bin/python3

import cv2     # for capturing videos
import math   # for mathematical operations
import matplotlib.pyplot as plt    # for plotting the images
import pandas as pd
from keras.preprocessing import image   # for preprocessing the images
import numpy as np    # for mathematical operations
from keras.utils import np_utils
from skimage.transform import resize   # for resizing images
from sklearn.model_selection import train_test_split
from glob import glob
from tqdm import tqdm


# load train vids into array
LEARNING_DIR = "/mnt/ams2/LEARNING/METEORS/"
YEARS = ['2020']


all_vids = []
for year in YEARS:
   vids = glob.glob(LEARNING_DIR + year + "/CROPS/*.mp4")
   for vid in vids:
      all_vids.append(vid)

# turn files list into PD obj
train = pd.DataFrame()
frame['video_name'] = all_vids
train = train[:-1]
train.head()
