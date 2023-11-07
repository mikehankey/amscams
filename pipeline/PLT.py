from Classes.Plotter import Plotter
import sys
import cv2
import numpy as np

if __name__ == "__main__":
   import sys
   extra_args = []

   if len(sys.argv) == 1:
      sys.argv.append("help")

   print("SYS:", sys.argv)
   for arg in sys.argv[2:]:
      print("ARG:", arg)
      extra_args.append(arg)
      
   PLT = Plotter(cmd=sys.argv[1], extra_args=extra_args)
   PLT.controller()
   PLT.plot_all_rad()
   #exit()
   if False:
      cat_stars = PLT.get_catalog_stars()
      blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
      ras = []
      decs = []
      for star in cat_stars:
         name,mag,ra,dec,x,y = star
         name = name.decode("utf-8")
         if mag <= 3:
            print(name, mag, ra, dec, x,y)
            x = int(x)
            y = int(y)
            ras.append(ra-180)
            decs.append(dec)
            cv2.circle(blank_image,(x,y), 3, (0,0,255), 1) 
      cv2.imwrite("/mnt/ams2/test.jpg", blank_image)


      import matplotlib
      import matplotlib.ticker as plticker
      #matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      #plt.scatter(ras, decs, color='yellowgreen', marker='.')
      fig = plt.figure(figsize=(8,6))
      ax = fig.add_subplot(111, projection="mollweide")
      ras = np.radians(ras)
      decs = np.radians(decs)
      ax.scatter(ras, decs)
      ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
      ax.grid(True)
      plt.savefig("/mnt/ams2/test2.png")

