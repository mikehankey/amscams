#!/usr/bin/python3 

import subprocess
import math
import ephem

def xy_to_radec (cal_file, x, y):
   cmd = "/usr/local/astrometry/bin/wcs-xy2rd -w " + cal_file + " -x " + str(x) + " -y " + str(y)
   output = subprocess.check_output(cmd, shell=True)
   (t, radec) = output.decode("utf-8").split("RA,Dec")
   radec = radec.replace('(', '')
   radec = radec.replace(')', '')
   radec = radec.replace('\n', '')
   radec = radec.replace(' ', '')
   ra, dec = radec.split(",")
   radd = float(ra)
   decdd = float(dec)
   ra= RAdeg2HMS(ra)
   #(h,m,s) = ra.split(":")
   #ra = h + " h " + m + " min"
   dec = Decdeg2DMS(dec)
   return(ra, dec, radd, decdd)


def radec_to_azel(ra,dec,lat,lon,alt, caldate):
   body = ephem.FixedBody()
   body._ra = ra
   body._dec = dec
   #body._epoch=ephem.J2000

   ep_date = ephem.Date(caldate)

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date =ep_date
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd
   #az = ephem.degrees(body.az)
   return(az,el)

def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out


def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out


