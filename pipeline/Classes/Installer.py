import glob
import os
import datetime
import numpy


class Installer():
   def __init__(self):
      self.now = datetime.datetime.now()
      self.pip_command = "pip3 install"
      self.apt_command = "apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages redis-server"
      self.pip_packages = [ 'numpy', 'daemon', 'pyephem', 'netifaces', 'pathlib', 'fitsio', 'pyfits', 'pillow', 'numpy', 'scipy', 'pandas', 'matplotlib', 'requests', 'scikit-image', 'sklearn', 'wand', 'pytesseract', 'pycrypto', 'astropy', 'sympy', 'vtk', 'ephem', 'suntime', 'flask', 'psutil', 'shapely', 'geopy', 'cartopy', 'pymap3d', 'simplekml', 'boto3', 'simplejson', 'flask_httpauth', 'flask-dynamo' ]
      self.apt_packages = []
      self.custom_packages = []

   def install_pips(self):
      for package in self.pip_packages:
 
         cmd = self.pip_command + " " + package
         eval_str = "import " + package
         try:
            exec(eval_str)
            print("Importing " + package)
         except:
            print("FAILED Importing " + package)
            print(cmd)
            os.system(cmd)

if __name__ == "__main__":
   IN = Installer()
   IN.install_pips()
