from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel
import numpy as np
from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression


def ransac_outliers(XS,YS,title):
   XS = np.array(XS)
   YS = np.array(YS)
   RXS = XS.reshape(-1, 1)
   RYS = YS.reshape(-1, 1)
   #oldway
   #XS.reshape(-1, 1)
   #YS.reshape(-1, 1)

   sd_min_max = [int(min(XS))-50, int(min(YS))-50, int(max(XS))+50, int(max(YS)+50)]

   if len(XS) > 0:
      lr = linear_model.LinearRegression()
      lr.fit(RXS,RYS)

      # find good and bad
      ransac = RANSACRegressor()
      ransac.fit(RXS,RYS)
      inlier_mask = ransac.inlier_mask_
      outlier_mask = np.logical_not(inlier_mask)

      # predict
      line_X = np.arange(RXS.min(),RXS.max())[:,np.newaxis]
      line_Y = lr.predict(line_X)
      line_y_ransac = ransac.predict(line_X)

      #print("I", inlier_mask)
      #print("O", outlier_mask)

   # make plot for ransac filter
   import matplotlib
   matplotlib.use('TkAgg')
   from matplotlib import pyplot as plt
   title += " " + str(len(RXS)) + " / " + str(len(XS))

   fig = plt.figure()
   plt.title(title)
   plt.scatter(RXS[inlier_mask], RYS[inlier_mask], color='yellowgreen', marker='.',
         label='Inliers')
   plt.scatter(RXS[outlier_mask], RYS[outlier_mask], color='gold', marker='.',
         label='Outliers')
   plt.plot(line_X, line_Y, color='navy', linewidth=1, label='Linear regressor')
   plt.plot(line_X, line_y_ransac, color='cornflowerblue', linewidth=1,
      label='RANSAC regressor')
   plt.legend(loc='lower right')
   plt.xlabel("X")
   plt.ylabel("Y")
   plt.xlim(min(XS)-25, max(XS)+100)
   plt.ylim(min(YS)-25, max(YS)+100)
   plt.gca().invert_yaxis()
   #plt.show()
   fig.clf()
   plt.close(fig)
   #plt.clf()
   #plt.cla()
   #plt.close()
   IN_XS = RXS[inlier_mask].tolist()
   IN_YS = RYS[inlier_mask].tolist()
   OUT_XS = RXS[outlier_mask].tolist()
   OUT_YS = RYS[outlier_mask].tolist()


   return(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X.tolist(),line_Y.tolist(),line_y_ransac.tolist(),inlier_mask.tolist(),outlier_mask.tolist())
