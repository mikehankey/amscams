# ONLY RUN THIS IF YOU WANT TO INSTALL 
# AMSCAMS IN A DEV ENV WITH conda
import os

# conda create -n amscams python=3.6

pip3 = [
'astride',
'flask-dynamo',
'suntime',
]

channels = [
'conda config --add channels conda-forge',
]

conda_packages = [
'-c conda-forge google-api-python-client',
'-c anaconda astropy',
'-c anaconda boto3',
'-c conda-forge chardet',
'-c anaconda cython',
'-c conda -forge python-daemon',
'-c anaconda dropbox',
'-c anaconda ephem',
'-c conda-forge fitsio',
'-c anaconda flask',
'-c conda-forge flask-httpauth',
'-c ioos geopy',
'-c conda-forge matplotlib',
'-c conda-forge netifaces',
'-c anaconda numpy',
'--channel https://conda.anaconda.org/menpo opencv3'
'-c anaconda pandas',
'-c conda-forge pathlib',
'-c anaconda pillow',
'-c anaconda psutil',
'-c anaconda pycrypto',
'-c anaconda pyephem',
'-c cefca pyfits',
'-c conda-forge pymap3d',
'-c conda-forge pyshp',
'-c conda-forge pytesseract',
'-c anaconda redis',
'-c anaconda requests',
'-c anaconda scikit-image',
'-c anaconda scipy',
'-c conda-forge shapely',
'-c anaconda simplejson',
'-c conda-forge simplekml',
'-c anaconda six',
'-c anaconda scikit-learn',
'-c anaconda sympy',
'-c conda-forge tensorflow-cpu',
'-c https://conda.binstar.org/travis uwsgi',
'-c conda-forge wand'

]

for pkg in conda_packages:
   cmd = "conda install -y " + pkg
   os.system(cmd)
