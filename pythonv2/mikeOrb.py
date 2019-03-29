#!/usr/bin/python3

from datetime import datetime
import numpy as np
import math
import json
import sys
from lib.SolverLib import earth_position
from lib.FileIO import load_json_file, save_json_file



##### Solving Meteor Orbit Steps #####
"""
 FIRST MILE STONE -- GEOCENTRIC RADIANT IN J2000
 - Goal 1
   Convert the observed radiant az/el to ra/dec.
 - Goal 2
   Convert the observed radiant ra/dec to J2000
 - Goal 3
   Convert the observed radiant ra/dec to geocentric
 - Goal 4 
   Convert the observed radiant ra/dec to geocentric ra/dec
 - Goal 5
   Convert the geocentric radiant ra/dec to J2000 ra/dec



"""
######################################


def final_orbit_vars(metorb, excel):
   # perihelion = peri
   # orbital eccentricity = e
   # inclination = i
   # longitude of ascending node =  node
   # Argument of perihelion =  omega 
   # Epoch = JD DATE? 
   metorb['final_orbit']['q'] = metorb['Ceplecha_vars']['orbit_q'] 
   metorb['final_orbit']['a'] = metorb['Ceplecha_vars']['orbit_a'] 
   metorb['final_orbit']['1_a'] = metorb['Ceplecha_vars']['orbit_1a'] 
   metorb['final_orbit']['e'] = metorb['Ceplecha_vars']['jacchia_e'] 
   metorb['final_orbit']['i'] = metorb['Ceplecha_vars']['tan_incl'] 
   metorb['final_orbit']['peri'] = metorb['Ceplecha_vars']['orbit_a'] * (1 -  metorb['Ceplecha_vars']['jacchia_e'])
   metorb['final_orbit']['omega'] = metorb['Ceplecha_vars']['jacchia_omega360']  
   #small bug here to fix node/solar longitude descrepency
   metorb['final_orbit']['node'] = metorb['Ceplecha_vars']['solar_longitude'] 
   metorb['final_orbit']['solar_longitude'] = metorb['Ceplecha_vars']['solar_longitude'] 
   metorb['final_orbit']['pi'] = metorb['Ceplecha_vars']['orbit_pi'] 
   metorb['final_orbit']['Vinf'] = metorb['meteor_input']['velocity'] 
   metorb['final_orbit']['Vgeo'] = metorb['radiants']['geocentric_radiant_position']['Vgeo']
   metorb['final_orbit']['Vh'] = metorb['earth_vars']['earth_vh']['Vh_km']
   metorb['final_orbit']['period'] = metorb['final_orbit']['a']**(3/2)
   metorb['final_orbit']['days_to_peri'] = metorb['Ceplecha_vars']['time_to_peri'] 
   metorb['final_orbit']['Q'] = metorb['Ceplecha_vars']['orbit_Q'] 
   metorb['final_orbit']['orbit_type'] = metorb['Ceplecha_vars']['orbit_type'] 
   metorb['final_orbit']['orbit_type2'] = metorb['Ceplecha_vars']['orbit_type2'] 
   metorb['final_orbit']['helio_rad_beta'] = metorb['earth_vars']['tan_beta_vars']['beta']  
   metorb['final_orbit']['helio_rad_lambda'] = metorb['earth_vars']['tan_beta_vars']['olambda']  
   metorb['final_orbit']['helio_rad_vh_km'] = metorb['earth_vars']['earth_vh']['Vh_km']  
   if metorb['final_orbit']['Q'] > 4.95:
      metorb['final_orbit']['jupiter_crossing'] = "Yes"
   else:
      metorb['final_orbit']['jupiter_crossing'] = "No"

   #mean anomaly (M)
   pday = 365.25 * metorb['final_orbit']['period']
   M = (360 / pday) * (pday - metorb['final_orbit']['days_to_peri']) 
   metorb['final_orbit']['M'] = M

   metorb['final_orbit']['rev_to_jump'] = 11.86224 / metorb['final_orbit']['period']
   if metorb['final_orbit']['node'] == metorb['final_orbit']['solar_longitude']:
      metorb['final_orbit']['meets_in'] = "descending node"
   else:
      metorb['final_orbit']['meets_in'] = "ascending node"

   metorb['final_orbit_plot'] = {}
   metorb['final_orbit_plot']['a'] = metorb['final_orbit']['a']
   metorb['final_orbit_plot']['M'] = metorb['final_orbit']['M']
   metorb['final_orbit_plot']['e'] = metorb['final_orbit']['e']
   metorb['final_orbit_plot']['I'] = metorb['final_orbit']['i']
   metorb['final_orbit_plot']['Peri'] = metorb['final_orbit']['omega']
   metorb['final_orbit_plot']['Node'] = metorb['final_orbit']['node']
   metorb['final_orbit_plot']['P'] = metorb['final_orbit']['period']
   metorb['final_orbit_plot']['q'] = metorb['final_orbit']['q']

   #metorb['final_orbit_plot']['jd_at_0h_utc'] = metorb['date_vars']['jd_at_0h_utc'] 
   metorb['final_orbit_plot']['event_time_utc'] = metorb['date_vars']['event_time_utc'] 
   metorb['final_orbit_plot']['jd_at_t'] = metorb['date_vars']['jd_at_t'] 
   metorb['final_orbit_plot']['J2000_jd_epoch'] =  2451545.0 

   final_json = {}
   final_json['orbit_vars'] = metorb
   save_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json", final_json)
   return(metorb, excel)

def Ceplecha_vars(metorb, excel):

   tan_lambda = metorb['earth_vars']['tan_beta_vars']['tan_lambda']  
   olambda = metorb['earth_vars']['tan_beta_vars']['olambda']  
   beta = metorb['earth_vars']['tan_beta_vars']['beta']  

   x_ecl = metorb['earth_vars']['earth_pos_vel']['earth_pos_x']  
   y_ecl = metorb['earth_vars']['earth_pos_vel']['earth_pos_y']  
   z_ecl = metorb['earth_vars']['earth_pos_vel']['earth_pos_z']  
   d_earth_ecl = metorb['earth_vars']['earth_pos_vel']['d_earth_ecl']  
   Vgeo = metorb['earth_vars']['earth_vel_ecl']['Vgeo'] 
   Vhx_au = metorb['earth_vars']['earth_vh']['Vhx_au'] 
   Vhz_au = metorb['earth_vars']['earth_vh']['Vhz_au'] 
   Vhy_au = metorb['earth_vars']['earth_vh']['Vhy_au'] 


   Vh_au= metorb['earth_vars']['earth_vh']['Vh_au']  
   
   tan_y_x_radians = math.atan2(y_ecl,x_ecl)
   tan_y_x_degrees = math.degrees(tan_y_x_radians)
   solar_longitude = 180 + tan_y_x_degrees 

   print("TAN YX RAD:", tan_y_x_radians)
   print("SOLAR LONGITUDE:", solar_longitude)

   if solar_longitude < 0:
      node1 = solar_longitude + 180
   else: 
      node1 = solar_longitude
   if node1 > 360:
      node2 = node1 - 360
   else:
      node2 = node1
   if node2 == 360:
      node2 = 0
   solar_longitude = node2 

   #=TAN(RADIANS(C13))/SIN(RADIANS(J13-C19))
   tan_incl = math.tan(math.radians(beta))/math.sin(math.radians(olambda-solar_longitude))
   metorb['Ceplecha_vars']['tan_incl0'] = tan_incl

   tan_incl1 = math.atan(tan_incl) * 180 / math.pi
   metorb['Ceplecha_vars']['tan_incl1'] = tan_incl1
   
   #if tan_incl1 < 0:
   #   tan_incl = tan_incl1 + 180
   #else:
   #   tan_incl = tan_incl1
   tan_incl = tan_incl1
   print("TAN INCL:", tan_incl)

   metorb['Ceplecha_vars']['solar_longitude'] = solar_longitude
   metorb['Ceplecha_vars']['tan_incl'] = tan_incl 

   # A 
   # =(0.01720209895^2*D4)/((2*0.01720209895^2)-(D4*H10^2))
   orbit_a = (0.01720209895**2 * d_earth_ecl) / ((2*0.01720209895**2)-(d_earth_ecl*Vh_au**2))
   orbit_1a = 1/orbit_a

   metorb['Ceplecha_vars']['orbit_a'] = orbit_a
   metorb['Ceplecha_vars']['orbit_1a'] = orbit_1a

   # A 
   print("D EARTH ECL:", d_earth_ecl)
   print("VH AU:", Vh_au)
   print ("A:", orbit_a) 
   print ("1/A:", orbit_1a) 

   # Ceplecha work area 1
   # calculate p
   #=((D4*-E10*SIN(RADIANS(A18)))-(D4*-F10*COS(RADIANS(A18))))/0.01720209895
   # D4 = d_earth_ecl 
   cpw1_sqrt_p_cosi = ((d_earth_ecl*-1*Vhx_au*math.sin(math.radians(solar_longitude))) - \
      (d_earth_ecl* -1 * Vhy_au * math.cos(math.radians(solar_longitude))))/ 0.01720209895 
   print("SQRT_P_COSI:", cpw1_sqrt_p_cosi)

   metorb['Ceplecha_vars']['cpw1_sqrt_p_cosi'] = cpw1_sqrt_p_cosi


   #=(-D4*-G10*SIN(RADIANS(A18)))/(0.01720209895*SIN(RADIANS(C19)))
   cpw1_sqrt_p_sini = (-1*d_earth_ecl * -1 * Vhz_au * math.sin(math.radians(solar_longitude)))/ \
      (0.01720209895*math.sin(math.radians(solar_longitude)))
   print("SQRT_P_SINI:", cpw1_sqrt_p_sini)

   metorb['Ceplecha_vars']['cpw1_sqrt_p_sini'] = cpw1_sqrt_p_sini

   # =G22/SIN(RADIANS(E18))
   cpw1_sqrt_p = cpw1_sqrt_p_sini / math.sin(math.radians(tan_incl1))
   cpw1_p = cpw1_sqrt_p ** 2
   cpw1_p_r = cpw1_p / d_earth_ecl 

   metorb['Ceplecha_vars']['cpw1_p'] = cpw1_p
   metorb['Ceplecha_vars']['cpw1_p_r'] = cpw1_p_r

   # G22 = 
   print("SQRT_P:", cpw1_sqrt_p)
   print("P:", cpw1_p)
   print("P/R:", cpw1_p_r)
   
   #cpw1_p = G24**2

   # Jacchia 
   jacchia_e2 = 1 - (cpw1_p / orbit_a)
   print("Jacchia e2:", jacchia_e2)
   metorb['Ceplecha_vars']['jacchia_e2'] = jacchia_e2
 
   jacchia_e = math.sqrt(jacchia_e2)
   print("Jacchia e:", jacchia_e)
   metorb['Ceplecha_vars']['jacchia_e'] = jacchia_e
 

   # NU
   #=(J24-1)/L18
   cos_nu = (cpw1_p_r-1)/jacchia_e
   nu_rad = math.acos(cos_nu)
   print("COS NU:", cos_nu)
   nu_deg = math.degrees(nu_rad)
   if nu_deg < 0:
      nu_deg = nu_deg + 360
   if nu_deg > 0:
      nu_deg = 360 - nu_deg
   else:
      nu_deg = 0-nu_deg

   metorb['Ceplecha_vars']['cos_nu'] = cos_nu
   metorb['Ceplecha_vars']['nu_deg'] = nu_deg 
   print("NURAD:", nu_rad)

   print("NU DEG:", nu_deg)

   # Jacchia Omega
   # might need to go back to the SL vs node2 and add an if statement here...
   jacchia_omega = 180 - nu_deg
   if jacchia_omega < 0:
      jacchia_omega360 = jacchia_omega + 360
   else:
      jacchia_omega360 = jacchia_omega 

   metorb['Ceplecha_vars']['jacchia_omega'] = jacchia_omega
   metorb['Ceplecha_vars']['jacchia_omega360'] = jacchia_omega360

   print("Jacchia Omega:", jacchia_omega)
   print("Jacchia Omega 360:", jacchia_omega360)

   # Ceplecha q
   orbit_q = orbit_a * (1-jacchia_e)
   metorb['Ceplecha_vars']['orbit_q'] = orbit_q
 
   print("Orbit Q:", orbit_q)

   #ORBIT PI
   #=IF((C19+H19)>360,C19+H19-360,C19+H19)
   if solar_longitude + jacchia_omega360 > 360:
      orbit_pi = solar_longitude + jacchia_omega360 - 360
   else:
      orbit_pi = solar_longitude + jacchia_omega360 

   print("ORBIT PI:", orbit_pi) 

   metorb['Ceplecha_vars']['orbit_pi'] = orbit_pi

   # eliptic or hyperbolic orbit
   if jacchia_e < 1:
      orbit_type = "elliptic"
   else:
      orbit_type = "hyperbolic"

   # retrograde or prograde
   if tan_incl1 > 90: 
      orbit_type2 = "retrograde"
   else:
      orbit_type2 = "prograde"

   metorb['Ceplecha_vars']['orbit_type'] = orbit_type 
   metorb['Ceplecha_vars']['orbit_type2'] = orbit_type2

   # days to perihelion
   orb_n  = 0.9856076686/(orbit_a*math.sqrt(orbit_a))
   print("ORB_N: ", orb_n)
   orb_tan_nu_2 = math.tan(math.radians(nu_deg/2))
   print("ORB TAN NU 2:", orb_tan_nu_2)
   orb_tan_e_2 = math.sqrt((1-jacchia_e)/(1+jacchia_e))*(orb_tan_nu_2)
   orb_E_2 =  math.atan(orb_tan_e_2)
   orb_E = orb_E_2 * 2

   print("E/2,E", orb_E_2, orb_E)

   print("ORB TAN E 2:", orb_tan_e_2)
   #=D33-(L18*SIN(D33))
   dp_M = orb_E-(jacchia_e*math.sin(orb_E))
   dp_M_deg = math.degrees(dp_M)
   dp_mn_days = dp_M_deg/orb_n
   print("DP_M:", dp_M)
   print("DP_MN days:", dp_mn_days)
   if dp_mn_days < 0:
      dp_mn_days = dp_mn_days * -1 

   metorb['Ceplecha_vars']['time_to_peri'] = dp_mn_days

   # Q (AU)
   if orbit_a * (1+jacchia_e) < 0:
      orbit_Q = "infinite"
   else: 
      orbit_Q = orbit_a * (1+jacchia_e) 
   print("orbit_Q", orbit_Q)
   metorb['Ceplecha_vars']['orbit_Q'] =orbit_Q 
   

   return(metorb, excel)


def tan_beta_vars(metorb, excel):
   # =-(G9/(SQRT(E9^2+F9^2)))
   # G9 = Vhz_km
   # E9 = Vhx_km
   # F9 = Vhy_km
   Vhx_km = metorb['earth_vars']['earth_vh']['Vhx_km'] 
   Vhz_km = metorb['earth_vars']['earth_vh']['Vhz_km'] 
   Vhy_km = metorb['earth_vars']['earth_vh']['Vhy_km'] 

   tan_beta = -1 * (Vhz_km/(math.sqrt(Vhx_km**2+Vhy_km**2)))
   tan_lambda = Vhy_km / Vhx_km
   beta = math.atan(tan_beta)*180/math.pi

   #=ATAN(B13)*180/PI() 
   atan_lambda = math.atan(tan_lambda)*180/math.pi

   lam1 = False
   lam2 = False
   lam3 = False
   lam4 = False
   if Vhx_km > 0 and Vhy_km > 0:
      lam1 = True
   if Vhx_km < 0 and Vhy_km > 0:
      lam2 = True
   if Vhx_km < 0 and Vhy_km < 0:
      lam3 = True
   if Vhx_km > 0 and Vhy_km < 0:
      lam4 = True

   if lam1 == True:
      olambda = 180 + atan_lambda
   if lam2 == True:
      olambda = atan_lambda + 360
   if lam3 == True:
      olambda = atan_lambda 
   if lam4 == True:
      olambda = 180 + atan_lambda 




   print("TAN BETA: ", tan_beta)
   print("TAN Lambda: ", tan_lambda)
   print("BETA: ", beta)
   print("ATAN LAMBDA: ", atan_lambda)
   print("LAMBDA: ", olambda)

   metorb['earth_vars']['tan_beta_vars']['tan_beta'] = tan_beta
   metorb['earth_vars']['tan_beta_vars']['tan_lambda']  = tan_lambda
   metorb['earth_vars']['tan_beta_vars']['beta']  = beta
   metorb['earth_vars']['tan_beta_vars']['atan_lambda']  = atan_lambda
   metorb['earth_vars']['tan_beta_vars']['olambda']  = olambda
   metorb['earth_vars']['tan_beta_vars']['lam1']  = lam1
   metorb['earth_vars']['tan_beta_vars']['lam2']  = lam2
   metorb['earth_vars']['tan_beta_vars']['lam3']  = lam3
   metorb['earth_vars']['tan_beta_vars']['lam4']  = lam4

   return(metorb, excel)

def earth_pos_vars(metorb, excel):

   input_date = metorb['meteor_input']['start_time']
   ex,ey,ez,evx,evy,evz,evl = earth_position (input_date)
   d_earth_ecl = np.sqrt(ex**2+ey**2+ez**2)

   Vgeo = metorb['earth_vars']['earth_vel_ecl']['Vgeo'] 

   metorb['earth_vars']['earth_pos_vel']['earth_pos_x'] = ex
   metorb['earth_vars']['earth_pos_vel']['earth_pos_y'] = ey
   metorb['earth_vars']['earth_pos_vel']['earth_pos_z'] = ez
   metorb['earth_vars']['earth_pos_vel']['earth_vel_x'] = evx
   metorb['earth_vars']['earth_pos_vel']['earth_vel_y'] = evy
   metorb['earth_vars']['earth_pos_vel']['earth_vel_z'] = evz
   metorb['earth_vars']['earth_pos_vel']['d_earth_ecl'] = d_earth_ecl

   one_au_10_8 = metorb['earth_vars']['earth_constants']['one_au_10_8']
   ang_of_ecl = metorb['earth_vars']['earth_constants']['angle_of_ecliptic_J2000']

   #V in x,y,z VxEarth, VyEarth, VzEarth, Va
   VxEarth = ((evx)/(86400)*(one_au_10_8*100000000))
   VyEarth = ((evy)/(86400)*(one_au_10_8*100000000))
   VzEarth = ((evz)/(86400)*(one_au_10_8*100000000))
   Va = math.sqrt(VxEarth**2+VyEarth**2+VzEarth**2)

   metorb['earth_vars']['earth_vel_ecl']['VxEarth'] = VxEarth
   metorb['earth_vars']['earth_vel_ecl']['VyEarth'] = VyEarth
   metorb['earth_vars']['earth_vel_ecl']['VzEarth'] = VzEarth
   metorb['earth_vars']['earth_vel_ecl']['Va'] = Va

   #Gravity vectors
   #=-F5*((COS(RADIANS(inputb!I13)))*COS(RADIANS(inputb!H13)))
   dec_geo = metorb['radiants']['geocentric_radiant_position']['geo_decJ2']
   ra_geo = metorb['radiants']['geocentric_radiant_position']['geo_raJ2']
   print("DEC GEO:", dec_geo)
   print("RA GEO:", ra_geo)
   Vgx = -1*Vgeo*((math.cos(math.radians(dec_geo)))*math.cos(math.radians(ra_geo)))

   #=-F5*((SIN(RADIANS(C1))*SIN(RADIANS(inputb!I13)))+(COS(RADIANS(C1))*COS(RADIANS(inputb!I13))*SIN(RADIANS(inputb!H13))))
   # F5 = Vgeo
   # C1 = angle of ecliptic
   # I13 Dec Geo J2A
   # H13 RA Geo J2
   Vgy = -1 * Vgeo * ((math.sin(math.radians(ang_of_ecl))*math.sin(math.radians(dec_geo))) + \
      math.cos(math.radians(ang_of_ecl)) * math.cos(math.radians(dec_geo))*math.sin(math.radians(ra_geo)))

   #=-F5*((COS(RADIANS(C1))*SIN(RADIANS(inputb!I13)))-
   # (SIN(RADIANS(C1))*COS(RADIANS(inputb!I13))*SIN(RADIANS(inputb!H13))))
   Vgz = -1 * Vgeo * ((math.cos(math.radians(ang_of_ecl))*math.sin(math.radians(dec_geo))) - \
      (math.sin(math.radians(ang_of_ecl)) *math.cos(math.radians(dec_geo))*math.sin(math.radians(ra_geo))))

   print("Vgeo:", Vgeo)
   print("Vgx:", Vgx)
   print("Vgy:", Vgy)
   print("Vgz:", Vgz)

   metorb['earth_vars']['earth_gravity_vectors']['Vgx'] = Vgx
   metorb['earth_vars']['earth_gravity_vectors']['Vgy'] = Vgy
   metorb['earth_vars']['earth_gravity_vectors']['Vgz'] = Vgz
   metorb['earth_vars']['earth_gravity_vectors']['Vgeo'] = Vgeo

   #VH x,y,z variables in km/s & au/d
   Vhx = Vgx + VxEarth 
   Vhy = Vgy + VyEarth
   Vhz = Vgz + VzEarth
   Vh = math.sqrt(Vhx**2+Vhy**2+Vhz**2)

   Vhx_au = Vhx/1731.456829
   Vhy_au = Vhy/1731.456829
   Vhz_au = Vhz/1731.456829

   Vh_au = Vh/1731.456829


   metorb['earth_vars']['earth_vh']['Vhx_km'] = Vhx
   metorb['earth_vars']['earth_vh']['Vhx_au'] = Vhx_au
   metorb['earth_vars']['earth_vh']['Vhy_km'] = Vhy
   metorb['earth_vars']['earth_vh']['Vhy_au'] = Vhy_au
   metorb['earth_vars']['earth_vh']['Vhz_km'] = Vhz
   metorb['earth_vars']['earth_vh']['Vhz_au'] = Vhz_au
   metorb['earth_vars']['earth_vh']['Vh_km'] = Vh
   metorb['earth_vars']['earth_vh']['Vh_au'] = Vh_au

   print("Vhx:", Vhx)
   print("Vhy:", Vhy)
   print("Vhz:", Vhz)
   print("Vh:", Vh)
   print("Vhx au:", Vhx_au)
   print("Vhy au:", Vhy_au)
   print("Vhz au:", Vhz_au)
   return(metorb, excel)


def geocentric_radiant_position(metorb,excel):
   lon,lat,alt = metorb['meteor_input']['end_point']
   velocity = metorb['meteor_input']['velocity']

   greenwich_sidereal_time = metorb['date_vars']['greenwich_sidereal_time']
   local_sidereal_hour_angle = metorb['date_vars']['local_sidereal_hour_angle']
   local_sidereal_time_deg = metorb['date_vars']['local_sidereal_time_deg']

   rad_ra = metorb['radiants']['observed_radiant_position']['rad_ra']
   rad_dec = metorb['radiants']['observed_radiant_position']['rad_dec']
   rad_raJ2 = metorb['radiants']['observed_radiant_position']['rad_raJ2']
   rad_decJ2 = metorb['radiants']['observed_radiant_position']['rad_decJ2']

   Vgeo = metorb['radiants']['geocentric_radiant_position']['Vgeo'] 

   print("RAD RAJ2:", rad_raJ2,rad_decJ2,Vgeo)

   geo_sidereal_time = lon + greenwich_sidereal_time

   #metorb['radiants']['geocentric_radiant_position']['geo_sidereal_time']  = geo_sidereal_time

   sin_beta = (-1*math.cos(math.radians(rad_decJ2))*math.sin(math.radians(rad_raJ2))*math.sin(math.radians(23.43928056)))+(math.sin(math.radians(rad_decJ2))*math.cos(math.radians(23.43928056)))
   sin_beta_asin = math.asin(sin_beta)
   beta_deg = math.degrees(sin_beta_asin)

   sin_labda = (math.cos(math.radians(rad_decJ2))*math.sin(math.radians(rad_raJ2))*math.cos(math.radians(23.43928056)))+(math.sin(math.radians(rad_decJ2))*math.sin(math.radians(23.43928056)))

   cos_phi = math.cos(math.radians(lat))
   #diurnal_dec = rad_dec + geo_sidereal_time

   delta_dec = -1*(26.58/velocity)*cos_phi* math.sin(math.radians(local_sidereal_hour_angle))*math.sin(math.radians(rad_decJ2))

   delta_ra = -1*(26.58/velocity)*cos_phi*math.cos(math.radians(local_sidereal_hour_angle))*(1/math.cos(math.radians(rad_decJ2)))

   diurnal_ra = rad_ra + delta_ra
   diurnal_dec = rad_dec + delta_dec
   new_az_height = local_sidereal_time_deg - diurnal_ra
   if new_az_height < 0:
      new_az_height = new_az_height + 360

   sin_phi = math.sin(math.radians(lat))

   sin_H = math.sin(math.radians(new_az_height))
   cos_H = math.cos(math.radians(new_az_height))
   sin_h = ( math.sin(math.radians( diurnal_dec)) * sin_phi)+(math.cos(math.radians(diurnal_dec))*cos_H*cos_phi)
   new_h = math.degrees(math.asin(sin_h))

   print("SIN_H:", sin_h)
   print("h:", new_h)
   metorb['sheet2_vars']['sin_h'] = sin_h
   metorb['sheet2_vars']['h'] = new_h

   apparent_radiant_altitude = new_h

   print("APPARENT RADIANT ALT:", apparent_radiant_altitude)

   print("Vgeo:", Vgeo)

   #=((input!C15-rekenmodule!F5)/(input!C15+rekenmodule!F5))*TAN(RADIANS(0.5*(90-Sheet5!G10)))
   # C15 = velocity
   # F5 = Vgeo
   # G10 = apparent_radiant_alt

   zenith_attraction = ((velocity - Vgeo)/(velocity+Vgeo))*math.tan(math.radians(0.5*(90-apparent_radiant_altitude)))
   
   print("Velocity:", velocity)
   print("VGeo:", Vgeo)
   print("ARA:", apparent_radiant_altitude)
 
   print("Zenith Attraction:", zenith_attraction)


   # out G26 = data for eq DEC
   half_ZA = math.degrees(math.atan(zenith_attraction))
   print("HALF ZA:", half_ZA)
   ZA = 2*math.degrees(math.atan(zenith_attraction))
   print("ZA:", ZA)
   print("APPARENT RADIANT ALT:", apparent_radiant_altitude)

   true_radiant_altitude = apparent_radiant_altitude - ZA


   #sheet5['D14'] = true_radiant_altitude

   print("TRUE RADIANT ALTITUDE:", true_radiant_altitude)


   print("APPARENT RADIANT ALT:", apparent_radiant_altitude)
   print("TRUE RADIANT ALT:", true_radiant_altitude)
   print("LAT:", lat)

   metorb['sheet4_vars'] = {}
   metorb['sheet2_vars']['ZA'] = ZA 
   metorb['sheet2_vars']['apparent_radiant_altitude'] = apparent_radiant_altitude 
   metorb['sheet2_vars']['true_radiant_altitude'] = true_radiant_altitude


   #=(-COS(RADIANS(Sheet5!D14))*SIN(RADIANS(Sheet5!E14)))/COS(RADIANS(output!G26))
   #geo_hr_sin_u = math.cos.radians(true_radiant_altitude)*math.sin.radians(true_radiant_azimuth))

   #print("GEO HR SIN DEC:", geo_hr_sin_dec)

   # =(-1*COS(RADIANS(Sheet5!E10))*G42)/COS(RADIANS(K42))

   print("DIURN DEC:", diurnal_dec)
   print("SIN H:", sin_H)
   print("TRUE RAD ALT:", true_radiant_altitude)
   print("APP RAD ALT:", apparent_radiant_altitude)
   sin_a = (-1*math.cos(math.radians(diurnal_dec))*sin_H)/math.cos(math.radians(apparent_radiant_altitude))
   print("SIN A:", sin_a)
   A = math.degrees(math.asin(sin_a))
   print("A:", A)
   if A == 360:
      A = 0
#   if A > 0:
#      true_radiant_azimuth = 180 - A  
#   else:
#      true_radiant_azimuth = 180+(360-A)
   true_radiant_azimuth = A
   if true_radiant_azimuth < 0:
      true_radiant_azimuth = true_radiant_azimuth + 360
   if true_radiant_azimuth == 360 :
      true_radiant_azimuth = 0 
   if true_radiant_azimuth > 360 :
      true_radiant_azimuth = true_radiant_azimuth - 360 


   #true_radiant_altitude = round(true_radiant_altitude,2)
   #true_radiant_azimuth = round(true_radiant_azimuth,2)
   #rad_dec = round(rad_dec,2)

   #=(-COS(RADIANS(Sheet5!D14))*SIN(RADIANS(Sheet5!E14)))/COS(RADIANS(output!G26))
   #=(-COS(RADIANS(true_radiant_alt))*SIN(RADIANS(true_radiant_az)))/COS(RADIANS(GEOCENTRIC_DEC))
   print("Zenith Attraction:", zenith_attraction)
   print("TRUE RADIANT ALT:", true_radiant_altitude)
   print("TRUE RADIANT AZ:", true_radiant_azimuth)
   print("RAD DEC:", rad_dec)

   #=SIN(RADIANS(Sheet5!D14))* SIN(RADIANS(input!D12))+ 
      #COS(RADIANS(Sheet5!D14))*COS(RADIANS(Sheet5!E14))*COS(RADIANS(input!D12))

   geo_sin_dec = math.sin(math.radians(true_radiant_altitude))*math.sin(math.radians(lat)) + \
      math.cos(math.radians(true_radiant_altitude))*math.cos(math.radians(true_radiant_azimuth))*math.cos(math.radians(lat))
   dec_radians = math.asin(geo_sin_dec)
   print("True Radiant Alt:", true_radiant_altitude)
   print("True Radiant Az:", true_radiant_azimuth)
   print("GEO SIN DEC:", geo_sin_dec)
   print("DEC RADIANS:", dec_radians) 
   metorb['sheet4_vars']['true_radiant_altitude'] = true_radiant_altitude 
   metorb['sheet4_vars']['lat'] = lat 
   metorb['sheet4_vars']['true_radiant_azimuth']  = true_radiant_azimuth
   metorb['sheet4_vars']['geo_sin_dec'] = geo_sin_dec
   #exit()

   geo_rad_dec = math.degrees(dec_radians)
   metorb['radiants']['geocentric_radiant_position']['geo_dec'] = geo_rad_dec

   #=(-COS(RADIANS(Sheet5!D14))*
   #SIN(RADIANS(Sheet5!E14)))/COS(RADIANS(output!G26))

   geo_sin_u = ( -1*math.cos(math.radians(true_radiant_altitude)) * \
       math.sin(math.radians(true_radiant_azimuth))/ math.cos(math.radians(geo_rad_dec)))

  

   geo_sin_u_rad = math.asin(geo_sin_u)
   geo_sin_u_deg = math.degrees(geo_sin_u_rad)
   if geo_sin_u_deg < 0:
      geo_sin_u_deg = geo_sin_u_deg + 360

   print("GEO SIN U:", geo_sin_u)
   print("GEO SIN U DEG:", geo_sin_u_deg)
   metorb['radiants']['geocentric_radiant_position']['geo_dec'] = geo_rad_dec
   metorb['radiants']['geocentric_radiant_position']['hour_angle_geo'] = geo_sin_u_deg 
   hour_angle_geo = geo_sin_u_deg
   sidereal_time_geo = metorb['radiants']['geocentric_radiant_position']['sidereal_time_geo']
   geo_ra = sidereal_time_geo - hour_angle_geo 
   if geo_ra < 0:
      geo_ra = geo_ra + 360
   geo_ra_last = geo_ra + 0.012808+(.005567*math.sin(math.radians(geo_ra))*math.tan(math.radians(geo_rad_dec)))

   metorb['radiants']['geocentric_radiant_position']['geo_ra'] = geo_ra 

   print("GEO RA:", geo_ra)
   print("GEO RA FINAL:", geo_ra_last)
   print("GEO DEC:", geo_rad_dec)

   #exit()



   return(metorb, excel)

def geocentric_vars(metorb, excel):
   velocity = metorb['meteor_input']['velocity']

   rad_dec = metorb['meteor_input']['rad_dec']
   rad_ra = metorb['meteor_input']['rad_ra']
   lon,lat,alt = metorb['meteor_input']['end_point']

   cos_rad_ra = np.cos(math.radians(rad_ra))
   sin_radians_23 = np.sin(math.radians(23.43928056))
   sin_radians_rad_dec = np.sin(np.radians(rad_dec))

   Vix = velocity * math.cos(math.radians(rad_ra))*math.cos(math.radians(rad_dec))
   Viy = velocity * ((math.sin(math.radians(23.43928056))*math.sin(math.radians(rad_dec)))+(math.cos(math.radians(23.43928056))*math.cos(math.radians(rad_dec))*math.sin(math.radians(rad_ra))))
   Viz = velocity * ((math.cos(math.radians(23.43928056))*math.sin(math.radians(rad_dec)))-(math.sin(math.radians(23.43928056))*math.cos(math.radians(rad_dec))*math.sin(math.radians(rad_ra))))

   metorb['eastpoint_vars']['eastpoint_vectors']['Vix'] = Vix
   metorb['eastpoint_vars']['eastpoint_vectors']['Viy'] = Viy
   metorb['eastpoint_vars']['eastpoint_vectors']['Viz'] = Viz

   viini_check = math.sqrt(Vix**2+Viy**2+Viz**2)
   metorb['eastpoint_vars']['eastpoint_vectors']['Viini_check'] = viini_check
   Ve = .4639*math.cos(math.radians(lat))

   ep_rad_ra = metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_ra']

   Vixc = Vix-(Ve*math.cos(math.radians(ep_rad_ra)))

   print("VIXC:", Vixc)
   print("RAD RA:", rad_ra)

   #THIS SHOULD BE THE EAST POINT RA NOT THE RADIANT RA!
   # EAST POINT RA = EP sidereal time - EP sidereal hour_angle
   eastpoint_hour_angle = metorb['eastpoint_vars']['eastpoint_radiant_position']['eastpoint_hour_angle']
    
# =C42-(I41*SIN(RADIANS(E30)))
   Viiyc = Viy-(Ve*math.sin(math.radians(ep_rad_ra)))
   print("Viiyc:", Viiyc)

   Vizc = Viz

   metorb['eastpoint_vars']['eastpoint_vectors']['Vixc'] = Vixc 
   metorb['eastpoint_vars']['eastpoint_vectors']['Viyc'] = Viiyc 
   metorb['eastpoint_vars']['eastpoint_vectors']['Vizc'] = Vizc 
   metorb['eastpoint_vars']['eastpoint_vectors']['Ve'] = Ve

   Vi_cor = math.sqrt(Vixc**2+Viiyc**2+Vizc**2)
   metorb['eastpoint_vars']['eastpoint_vectors']['Vi_cor'] = Vi_cor

   Vgeo = math.sqrt((Vi_cor**2)-(11.17**2))

   metorb['earth_vars']['earth_vel_ecl']['Vgeo'] = Vgeo
   metorb['eastpoint_vars']['eastpoint_vectors']['Vgeo'] = Vgeo
   metorb['radiants']['geocentric_radiant_position']['Vgeo'] = Vgeo


   return(metorb,excel)



def geo_radiant_to_j2000(metorb,excel):
   dec_epoch = metorb['radiants']['geocentric_radiant_position']['geo_dec'] 
   ra_epoch = metorb['radiants']['geocentric_radiant_position']['geo_ra'] 
   dec_epoch_rad = math.radians(dec_epoch)
   ra_epoch_rad = math.radians(ra_epoch)
   zeta_deg_rad = metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg_rad'] 
   theta_deg_rad = metorb['eastpoint_vars']['eastpoint_sin_u']['theta_deg_rad'] 

   JKJ2_A = math.cos(dec_epoch_rad)*math.sin(ra_epoch_rad+zeta_deg_rad)
   JKJ2_B = (math.cos(theta_deg_rad)*math.cos(dec_epoch_rad)*math.cos(ra_epoch_rad+zeta_deg_rad))- \
      (math.sin(theta_deg_rad)*math.sin(dec_epoch_rad))
   JKJ2_C = (math.sin(theta_deg_rad)*math.cos(dec_epoch_rad)*math.cos(ra_epoch_rad+zeta_deg_rad))+ \
      (math.cos(theta_deg_rad)*math.sin(dec_epoch_rad))

   JKJ2_ra_min_z = math.atan2(JKJ2_A, JKJ2_B)
   print("JK ra_min_z", JKJ2_ra_min_z) 
   geo_raJ2 = math.degrees(JKJ2_ra_min_z + zeta_deg_rad)
   if geo_raJ2 < 0:
      geo_raJ2 = geo_raJ2 + 360

   geoJ2_delta_rad = math.asin(JKJ2_C)
   geo_decJ2 = math.degrees(geoJ2_delta_rad)

   metorb['radiants']['geocentric_radiant_position']['geo_raJ2']  = geo_raJ2
   metorb['radiants']['geocentric_radiant_position']['geo_decJ2']  = geo_decJ2
   print("GEO RAJ2", geo_raJ2)
   print("GEO DECJ2", geo_decJ2)
   return(metorb,excel)

def observed_radiant_to_j2000(metorb,excel):
   # have to do eastpoint var setup first
   rad_dec = metorb['meteor_input']['rad_dec']
   rad_ra = metorb['meteor_input']['rad_ra']
   theta_deg = metorb['eastpoint_vars']['eastpoint_sin_u']['theta_deg'] 
   theta_deg_rad = metorb['eastpoint_vars']['eastpoint_sin_u']['theta_deg_rad'] 
   zeta_deg = metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg'] 
   zeta_deg_rad = metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg_rad'] 
   epoch = metorb['eastpoint_vars']['eastpoint_sin_u']['epoch'] 

   #zeta_deg_rad = math.radians(eastpoint['L49'])
   rad_ra_plus_zeta_deg = math.radians(rad_ra)+math.radians(zeta_deg)

   print("RAD DEC:", rad_dec)
   ORJ2_A = math.cos(math.radians(rad_dec))*math.sin(math.radians(rad_ra)+math.radians(zeta_deg))
   ORJ2_B = ( math.cos(math.radians(theta_deg)) * math.cos(math.radians(rad_dec)) * math.cos(math.radians(rad_ra+math.radians(zeta_deg))) -( math.sin(math.radians(theta_deg)) * math.sin(math.radians(rad_dec))))
   ORJ2_C = ( math.sin(math.radians(theta_deg)) * math.cos(math.radians(rad_dec)) * \
      math.cos(rad_ra_plus_zeta_deg))+ \
      (math.cos(math.radians(theta_deg))* math.sin(math.radians(rad_dec)))

   print("ORJ2_A:", ORJ2_A)
   print("ORJ2_B:", ORJ2_B)
   print("ORJ2_C:", ORJ2_C)
   metorb['eastpoint_vars']['eastpoint_sin_u']['ORJ2_A']  = ORJ2_A
   metorb['eastpoint_vars']['eastpoint_sin_u']['ORJ2_B']  = ORJ2_B
   metorb['eastpoint_vars']['eastpoint_sin_u']['ORJ2_C']  = ORJ2_C
 
   metorb['eastpoint_vars']['eastpoint_radiant_position']['epoch']  = epoch
 
   #I30 = radians of EP RA

   ep_ra = metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_ra']

   EP_BCD_A = math.cos(0)*math.sin(epoch+zeta_deg_rad)
   metorb['eastpoint_vars']['eastpoint_sin_u']['EP_BCD_A']  = EP_BCD_A

   # =(COS(P50)*COS(J30)*COS(I30+L50))-(SIN(P50)*SIN(J30))
   EP_BCD_B = math.cos(theta_deg_rad)*math.cos(0)*math.cos(epoch+zeta_deg_rad)-(math.sin(theta_deg_rad)*math.sin(0))
   metorb['eastpoint_vars']['eastpoint_sin_u']['EP_BCD_B']  = EP_BCD_B

   #=(SIN(P50)*COS(J30)*COS(I30+L50))+(COS(P50)*SIN(J30))
   EP_BCD_C = (math.sin(theta_deg_rad)*math.cos(0)*math.cos(epoch+zeta_deg_rad))+(math.cos(theta_deg_rad)*math.sin(0))
   metorb['eastpoint_vars']['eastpoint_sin_u']['EP_BCD_C']  = EP_BCD_C


   print("EP_BCD_A:", EP_BCD_A)

   ra_min_z = math.atan2(EP_BCD_A,EP_BCD_B)
   print("RA MIN Z: ", ra_min_z)
   metorb['eastpoint_vars']['eastpoint_j2000']['ra_min_z'] = ra_min_z

   ra_min_z_plus_zeta = math.degrees(ra_min_z+math.radians(zeta_deg))
   #N54 = zeta_deg_rad + ra_min_z

   if ra_min_z_plus_zeta < 0:
      rad_raJ2 = ra_min_z_plus_zeta + 360
   else:
      rad_raJ2 = ra_min_z_plus_zeta

   delta_rad = math.asin(EP_BCD_C)
   delta_j2000 = math.degrees(delta_rad)
   print("Delta Rad:", delta_rad)
   print("Delta J2000:", delta_j2000)
   rad_decJ2 = delta_j2000
   metorb['eastpoint_vars']['eastpoint_j2000']['ep_ra_J2000'] = rad_decJ2

   metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_ra_J2000'] = rad_raJ2
   metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_dec_J2000'] = rad_decJ2

   metorb['eastpoint_vars']['eastpoint_j2000']['ep_ra_J2000'] = rad_raJ2
   metorb['eastpoint_vars']['eastpoint_j2000']['ep_dec_J2000'] = rad_decJ2

   print("J2000 RA/DEC :", rad_raJ2, rad_decJ2)
   #output['H21'] = rad_raJ2
   #output['I21'] = rad_decJ2

   # Now do J2000 for obs radiant
   obs_ra_min_z = math.atan2(ORJ2_A, ORJ2_B)
   print("RAMINZ", obs_ra_min_z)

   print("OBS RA MIN Z:", obs_ra_min_z)
   print("OBS ZETA DEG RAD:", zeta_deg_rad)
   obs_rad_raJ2 = math.degrees(obs_ra_min_z + zeta_deg_rad)

   if obs_rad_raJ2 < 0:
      obs_rad_raJ2 = obs_rad_raJ2 + 360

   print("RADRAJ2:", obs_rad_raJ2)

   metorb['radiants']['observed_radiant_position']['rad_raJ2'] = obs_rad_raJ2

   obs_delta_rad = math.asin(ORJ2_C)
   print("DELTA:", obs_delta_rad)
   rad_decJ2 = math.degrees(obs_delta_rad)
   metorb['radiants']['observed_radiant_position']['rad_decJ2'] = rad_decJ2 



   return(metorb,excel)

def setup_eastpoint_vars(metorb,excel):
   eastpoint_el  = 0
   eastpoint_az = 90
   lat = metorb['meteor_input']['end_point'][1]
   lon = metorb['meteor_input']['end_point'][0]
   rad_ra = metorb['meteor_input']['rad_ra']
   rad_dec = metorb['meteor_input']['rad_dec']
   T = metorb['date_vars']['T'] 
   t = metorb['date_vars']['t']

   local_sidereal_time_deg = metorb['date_vars']['local_sidereal_time_deg']

   #=SIN(RADIANS(eastpoint!D18))*SIN(RADIANS(eastpoint!D11))+COS(RADIANS(eastpoint!D18))*COS(RADIANS(eastpoint!C18))*COS(RADIANS(eastpoint!D11))

   eastpoint_sin_dec = math.sin(math.radians(eastpoint_el))*math.sin(math.radians(lat))+math.cos(math.radians(eastpoint_el))*math.cos(math.radians(eastpoint_az))*math.cos(math.radians(lat))
   dec_radians = math.asin(eastpoint_sin_dec)
   metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_dec'] = eastpoint_sin_dec

   eastpoint_sin_u = (-1*(math.cos(math.radians(eastpoint_el))*math.sin(math.radians(eastpoint_az))))/math.cos(math.radians(eastpoint_sin_dec))
   eastpoint_sin_u_rad = math.asin(eastpoint_sin_u)
   eastpoint_sin_u_deg = math.degrees(eastpoint_sin_u_rad)
   if eastpoint_sin_u_deg < 0:
      eastpoint_sin_u_deg = eastpoint_sin_u_deg + 360
   eastpoint_hour_angle = eastpoint_sin_u_deg

   metorb['eastpoint_vars']['eastpoint_sin_u']['sin_dec'] = eastpoint_sin_dec
   metorb['eastpoint_vars']['eastpoint_sin_u']['dec_radians'] = dec_radians
   metorb['eastpoint_vars']['eastpoint_sin_u']['eastpoint_sin_u'] = eastpoint_sin_u
   metorb['eastpoint_vars']['eastpoint_sin_u']['eastpoint_sin_u_rad'] = eastpoint_sin_u_rad
   metorb['eastpoint_vars']['eastpoint_sin_u']['eastpoint_sin_u_deg'] = eastpoint_sin_u_deg
   metorb['eastpoint_vars']['eastpoint_sin_u']['eastpoint_hour_angle'] = eastpoint_sin_u_deg
   eastpoint_hour_angle = eastpoint_sin_u_deg

   sidereal_time_geo = metorb['radiants']['geocentric_radiant_position']['sidereal_time_geo'] 


   eastpoint_sidereal_hour_diff = sidereal_time_geo - eastpoint_hour_angle
   #print(str(local_sidereal_time_deg) + " - " + str(eastpoint_hour_angle) + " = " + str(eastpoint_sidereal_hour_diff))
   eastpoint_epoch_ra = eastpoint_sidereal_hour_diff # epoch_RA

   metorb['eastpoint_vars']['eastpoint_radiant_position']['hour_angle_ep'] = eastpoint_hour_angle 
   metorb['eastpoint_vars']['eastpoint_radiant_position']['sidereal_time_ep'] = sidereal_time_geo
   metorb['eastpoint_vars']['eastpoint_radiant_position']['eastpoint_hour_angle'] = eastpoint_hour_angle


   metorb['eastpoint_vars']['eastpoint_radiant_position']['ep_ra'] = eastpoint_epoch_ra

   metorb['eastpoint_vars']['eastpoint_sin_u']['eastpoint_epoch_ra'] = eastpoint_epoch_ra

   theta_arcsec=((2004.3109-(0.8533*T)-(0.000217*(T*T)))*t)-((0.42665+(0.000217*T))*(T*T))-(0.041833*(t*t*t))
   theta_deg = (theta_arcsec/60)/60

   metorb['eastpoint_vars']['eastpoint_sin_u']['theta_arcsec'] = theta_arcsec
   metorb['eastpoint_vars']['eastpoint_sin_u']['theta_deg'] = theta_deg


   epoch = math.radians(eastpoint_epoch_ra)

   metorb['eastpoint_vars']['eastpoint_sin_u']['epoch'] = epoch


   zeta_arcsec = ((2306.2181+(1.39656*T)-(0.000139*(T*T)))*t)+((0.30188-(0.000344*T))*(t*t))+(0.017998*(t*t*t))
   zeta_deg = (zeta_arcsec/60)/60

   metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_arcsec'] = zeta_arcsec
   metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg'] = zeta_deg


   #WRONG?
   ra_epoch_radians = math.radians(rad_ra+math.radians(zeta_deg))

   zeta_deg_radians = math.radians(zeta_deg)
   theta_deg_radians = math.radians(theta_deg)
   rad_dec_radians = math.radians(rad_dec)

   metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg'] = zeta_deg
   metorb['eastpoint_vars']['eastpoint_sin_u']['rad_dec_radians'] = rad_dec_radians
   metorb['eastpoint_vars']['eastpoint_sin_u']['zeta_deg_rad'] = zeta_deg_radians
   metorb['eastpoint_vars']['eastpoint_sin_u']['theta_deg_rad'] = theta_deg_radians

   cos_phi = math.cos(math.radians(lat))
   metorb['eastpoint_vars']['eastpoint_sin_u']['cos_phi'] = cos_phi

   return(metorb, excel)




def compute_obs_hour_angle(metorb,excel):

   # cos radiant el * sin radiant az / cos rad_dec

   rad_az = metorb['meteor_input']['rad_az']
   rad_el = metorb['meteor_input']['rad_el']
   rad_dec = metorb['meteor_input']['rad_dec']

   print("RAD AZ,EL,DEC:", rad_az,rad_el,rad_dec)

   sin_u = (-1*math.cos(math.radians(rad_el))*math.sin(math.radians(rad_az)))/math.cos(math.radians(rad_dec))

   sin_u_radians = math.asin(sin_u)
   sin_u_degrees = math.degrees(sin_u_radians)
   if sin_u_degrees < 0:
      sin_u_degrees = sin_u_degrees + 360

   print("SIN_U", sin_u)
   local_sidereal_hour_angle = sin_u_degrees
   #output['E21'] = local_sidereal_hour_angle
   #sheet2['F10'] = sin_u
   #sheet2['G10'] = sin_u_radians
   #sheet2['H10'] = sin_u_degrees
   #sheet2['N10'] = local_sidereal_hour_angle

   # compute observed radiant RA from sidereal & hourangle
   #output['F21'] = output['D21'] - local_sidereal_hour_angle

   #metorb['date_vars']['local_sidereal_time_deg'] = greenwich_sidereal_time

   rad_ra = metorb['date_vars']['local_sidereal_time_deg'] - local_sidereal_hour_angle 


   if rad_ra < 0:
      rad_ra = rad_ra + 360

   print("Hour Angle: ", local_sidereal_hour_angle)
   print("RAD RA: ", rad_ra)
   metorb['date_vars']['local_sidereal_hour_angle'] = local_sidereal_hour_angle
   metorb['meteor_input']['rad_ra'] = rad_ra
   metorb['radiants']['observed_radiant_position']['hour_angle'] = local_sidereal_hour_angle
   metorb['radiants']['observed_radiant_position']['rad_ra'] = rad_ra

   return(metorb, excel)


def compute_obs_rad_dec(metorb,excel):
   rad_alt = math.radians(metorb['meteor_input']['rad_el'])
   rad_lat = math.radians(metorb['meteor_input']['end_point'][1])
   rad_az = math.radians(metorb['meteor_input']['rad_az'])
   #sin dec = SIN(RADIANS(rad_alt))*SIN(RADIANS(rad_lat))+COS(RADIANS(rad_alt))*COS(RADIANS(rad_az))*COS(RADIANS(rad_lat))
   sin_dec = math.sin(rad_alt)*math.sin(rad_lat)+math.cos(rad_alt)*math.cos(rad_az)*math.cos(rad_lat)
   dec_radians = math.asin(sin_dec)
   rad_dec = math.degrees(dec_radians)
 
   metorb['meteor_input']['rad_dec'] = rad_dec
   metorb['radiants']['observed_radiant_position']['rad_dec'] = rad_dec

   metorb['sheet2_vars'] = {} 
   metorb['sheet2_vars']['sin_dec'] = sin_dec
   metorb['sheet2_vars']['dec_radians'] = dec_radians
   metorb['sheet2_vars']['rad_dec'] = rad_dec

   return(metorb,excel)

  
def date_vars(metorb, excel):
   input_date = metorb['meteor_input']['start_time']
   imp_lon = metorb['meteor_input']['end_point'][0]
   yr_cor = int(input_date[0:4])
   mon_cor = int(input_date[5:7])
   day = int(input_date[8:10])
   hour = int(input_date[11:13])
   min = int(input_date[14:16])
   sec = int(input_date[17:19])
   min_f = min + sec / 60
   hour_f = hour + (min_f / 60)
   day_f = day + (hour_f / 24)

   day_str = str(yr_cor) + "-" + str(mon_cor) + "-" + str(day) + "T00:00:00"
   py_datetime = datetime.strptime(day_str, "%Y-%m-%dT%H:%M:%S")
   day_of_year = py_datetime.timetuple().tm_yday - 1


   # from eastpoint A & B (year / 100 and quarter?)
   year_100 = int(yr_cor/100)
   year_100_25 = 2 - year_100+int(year_100/4)
   JD_at_t = int(365.25*(yr_cor+4716))+int(30.6001*(mon_cor+1))+day_f+year_100_25-1524.5

   T = (JD_at_t - 2451545)/36525
   t = (2451545- JD_at_t)/36525

   jd_at_0h_utc =int(365.25*(yr_cor+4716))+int(30.6001*(mon_cor+1))+day+year_100_25-1524.5

   theta_rad = (280.46061837+360.98564736629*(JD_at_t-2451545)+((0.000387933*(T*2))-(T**3/38710000)))
   maal_360 = theta_rad/360


   greenwich_sidereal_time = theta_rad-(int(maal_360)*360)
   if greenwich_sidereal_time < 0:
      greenwich_sidereal_time = greenwich_sidereal_time + 360
   geo_sidereal_time_deg = metorb['meteor_input']['end_point'][0]+greenwich_sidereal_time

   # year as decimal
   #year_dec =input!C22+(Sheet2!I33/365)
   # C22 = year 
   # I33 = number of days this year with HMS decimal placesA
   day_num_f = day_of_year + (hour_f/24)
   year_dec = yr_cor + (day_num_f /365)

   metorb['radiants']['observed_radiant_position']['sidereal_time'] = greenwich_sidereal_time + imp_lon 
   metorb['radiants']['geocentric_radiant_position']['sidereal_time_geo'] = geo_sidereal_time_deg

   metorb['date_vars']['start_time_JD'] = JD_at_t
   metorb['date_vars']['event_time_utc'] = str(yr_cor) + "-" + str(mon_cor) + "-" + str(day) + " " + str(hour) + ":" + str(min) + ":" + str(sec)
   metorb['date_vars']['year'] = yr_cor
   metorb['date_vars']['mon'] = mon_cor
   metorb['date_vars']['day'] = day
   metorb['date_vars']['hour'] = hour 
   metorb['date_vars']['min'] = min
   metorb['date_vars']['sec'] = sec
   metorb['date_vars']['min_f'] = min_f
   metorb['date_vars']['hour_f'] = hour_f
   metorb['date_vars']['day_f'] = day_f
   metorb['date_vars']['day_num_f'] = day_num_f 
   metorb['date_vars']['day_dec'] = day_num_f 
   metorb['date_vars']['day_of_year'] = day_f
   metorb['date_vars']['year_100'] = year_100 
   metorb['date_vars']['year_dec'] = year_dec
   metorb['date_vars']['jd_at_0h_utc'] = jd_at_0h_utc
   metorb['date_vars']['jd_at_t'] = JD_at_t
   metorb['date_vars']['T'] = T
   metorb['date_vars']['T'] = T
   metorb['date_vars']['t'] = t
   metorb['date_vars']['theta_rad'] = theta_rad
   metorb['date_vars']['maal_360'] = maal_360
   metorb['date_vars']['year_100'] = year_100 
   metorb['date_vars']['year_100_25'] = year_100_25
   metorb['date_vars']['greenwich_sidereal_time'] = greenwich_sidereal_time
   metorb['date_vars']['local_sidereal_time_deg'] = greenwich_sidereal_time + imp_lon 
   metorb['date_vars']['geo_sidereal_time_deg'] = geo_sidereal_time_deg

   return(metorb,excel)




orbit_vars = load_json_file("orbits/orbit-vars.json")
metorb = orbit_vars['orbit_vars']




excel = {}
excel['input'] = {}
excel['output'] = {}
excel['inputb'] = {}
excel['rekenmodule'] = {}
excel['eastpoint'] = {}
excel['eastpoint'] = {}
excel['sheet2'] = {}
excel['sheet3'] = {}
excel['sheet4'] = {}
excel['sheet5'] = {}

metorb, excel = date_vars(metorb, excel)
metorb, excel = compute_obs_rad_dec(metorb,excel)
metorb, excel = compute_obs_hour_angle(metorb,excel)
metorb, excel = setup_eastpoint_vars(metorb,excel)
metorb, excel = observed_radiant_to_j2000(metorb,excel)
metorb, excel = geocentric_vars(metorb,excel)
metorb, excel = geocentric_radiant_position(metorb,excel)
metorb, excel = geo_radiant_to_j2000(metorb,excel)
metorb, excel = earth_pos_vars(metorb, excel)
metorb, excel = tan_beta_vars(metorb, excel)
metorb, excel = Ceplecha_vars(metorb, excel)
metorb, excel = final_orbit_vars(metorb, excel)

print(json.dumps(metorb, indent=4, sort_keys=False))
