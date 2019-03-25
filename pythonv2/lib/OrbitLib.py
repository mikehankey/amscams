from lib.FileIO import load_json_file
from lib.SolverLib import earth_position
import numpy as np 
import math


def print_eastpoint(eastport):
   ep = eastport
   print("""
   eastport
   --------
   Vix          Viy          Viz          Viini check     Ve     {:f}
   {:f} {:f} {:f} {:f}

   Vixc         Viiyc        Vizc         Vi cor
   {:f} {:f} {:f} {:f}

   """.format(ep['I41'], ep['B42'], ep['C42'], ep['D42'], ep['F42'],ep['B45'],ep['C45'],ep['D45'], ep['F45']))

def print_input(input):
   print("""
   input
   -----

   INPUT           Long E       Lat N
   location        {:f}     {:f}   degrees 

   INPUT           Vini
   Meteor Speed    {:f}

   INPUT           Azimuth      Altitude   (apparent) 
   Obs. Radiant    {:0.2f}       {:0.2f}       degrees

   INPUT           Year      Month      Day
   date:           {:d}      {:d}          {:d}

   INPUT           Hour      Min        Sec
   time (UTC)      {:d}        {:d}         {:d}


   input heliocentric ecliptic Earth coordinates & velocity for date & time of meteor
   Earth Position  X             Y              Z         
   position(t)     {:0.9f}   {:0.9f}   {:0.9f}   AU
   velocity(t)     {:0.9f}   {:0.9f}    {:0.9f}   AU/day 
   """.format(input['C12'], input['D12'], input['C15'], input['C19'], input['D19'], input['C22'], input['D22'],input['E22'],input['C24'],input['D24'],input['E24'],input['H17'], input['I17'],input['J17'],input['H18'],input['I18'],input['J18']))

def print_output(output):
   print("""
   output
   ------
   OBSERVED RADIANT POSITION
   OUTPUT                                     equinox of date                   equinox J2000
   local             (deg)     hour angle     RA         DEC                    RA       DEC
   sidereal time     {:0.2f}     {:0.2f}        {:0.4f}     {:0.4f}                 {:0.4f}   {:0.4f}
   """.format(output['D21'], output['E21'],output['F21'],output['G21'],output['H21'],output['I21']))

   print(""" 
   GEOCENTRIC RADIANT POSITION
   OUTPUT                                     equinox of date                   equinox J2000       km/s
   local             (deg)     hour angle     RA         DEC                    RA       DEC        Vgeo
   sidereal time     {:0.2f}        {:0.2f}         {:0.2f}       {:0.2f}                   {:0.2f}     {:0.2f}       {:0.2f}
   """.format(output['D26'], output['E26'],output['F26'],output['G26'],output['H26'],output['I26'], output['J26']))
   

def print_rekenmodule(RM):

   print(""" 
   rekenmodule
   -----------
   angle of ecliptic (2000.0) {:f}     1 AU (10^8)    {:f}

   x ecl.      y ecl.      z ecl.     D_earth_ecl.  V in x,y,z   VxEarth     VyEarth     VzEarth     Va
   {:f}   {:f}   {:f}   {:f}                   {:f}   {:f}   {:f}   {:f}
                                                    Vgeo(km/s)   {:f}
   """.format(RM['C1'],RM['F1'],RM['A4'],RM['B4'],RM['C4'],RM['D4'],RM['F4'],RM['G4'],RM['H4'],RM['I4'],RM['F5'] ))

   print("""
   Vgx      Vgy	     Vgz      Vgeo     Vhx      Vhy      Vhz      Vh
   {:f} {:f} {:f} {:f} {:f} {:f} {:f} {:f}   km/s
                                       {:f} {:f} {:f} {:f}   AU/soldag	Ceplecha

   """.format( RM['A9'], RM['B9'], RM['C9'], RM['D9'], RM['E9'], RM['F9'], RM['G9'], RM['H9'], RM['E10'], RM['F10'], RM['G10'], RM['H10'] ))


def default_rekenmodule(RM):
   #constants
   RM['C1'] = 23.43929111
   RM['F1'] = 1.495978707

   # Earth position and velocity vars 
   RM['A4'] = 0
   RM['B4'] = 0
   RM['C4'] = 0
   RM['D4'] = 0
   RM['F4'] = 0
   RM['G4'] = 0
   RM['H4'] = 0
   RM['I4'] = 0 
   RM['F5'] = 0

   # Earth Vg Vars (Vgx, Vgy Vgz etc)
   RM['A9'] = 0
   RM['B9'] = 0
   RM['C9'] = 0
   RM['D9'] = 0
   RM['E9'] = 0
   RM['F9'] = 0
   RM['G9'] = 0
   RM['H9'] = 0
   # 2nd row
   RM['E10'] = 0
   RM['F10'] = 0
   RM['G10'] = 0
   RM['H10'] = 0
   return(RM)


def setup_objects(meteor_sol_json_file):
   input = {}
   input_b = {}
   output = {}
   rekenmodule = {}
   sheet2 = {}
   sheet3 = {}
   sheet4 = {}
   sheet5 = {}
   eastpoint = {}

   meteor = load_json_file(meteor_sol_json_file)
   input_date = meteor['meteor']['start_time']
   rad_el = meteor['meteor']['rad_el']
   rad_az = meteor['meteor']['rad_az']
   lon, lat,alt = meteor['meteor']['end_point']
   velocity = meteor['meteor']['velocity']

   input['mike'] = {}
   input['mike']['input_date'] = input_date

   # Meteor Impact Point
   input['C12'] = lon
   input['D12'] = lat
   # Meteor Velocity
   input['C15'] = velocity
   # Radiant AZ/EL
   input['C19'] = rad_az
   input['D19'] = rad_el

   rekenmodule = default_rekenmodule(rekenmodule)

   output['F21'] = meteor['meteor']['rad_ra']
   output['G21'] = meteor['meteor']['rad_dec']
   output['E21'] = 0
   output['H21'] = 0
   output['I21'] = 0
   output['D26'] = 0
   output['E26'] = 0
   output['F26'] = 0
   output['G26'] = 0
   output['H26'] = 0
   output['I26'] = 0
   output['J26'] = 0


   return(input, input_b, output, rekenmodule, sheet2, sheet3, sheet4, sheet5, eastpoint,meteor)

def date_var_setup(input, eastpoint, output,meteor):
   input_date = input['mike']['input_date']
   yr_cor = int(input_date[0:4])
   mon_cor = int(input_date[5:7])
   day = int(input_date[8:10])
   hour = int(input_date[11:13])
   min = int(input_date[14:16])
   sec = int(input_date[17:19])
   min_f = min + sec / 60
   hour_f = hour + (min_f / 60)
   day_f = day + (hour_f / 24)
   R29 = int(yr_cor/100)
   S29 = 2 - R29+int(R29/4)
   JD_at_t = int(365.25*(yr_cor+4716))+int(30.6001*(mon_cor+1))+day_f+S29-1524.5

   T = (JD_at_t - 2451545)/36525
   t = (2451545- JD_at_t)/36525

   theta_rad = (280.46061837+360.98564736629*(JD_at_t-2451545)+((0.000387933*(T*2))-(T**3/38710000)))
   maal_360 = theta_rad/360

   print("T:", T)
   print("t:", t)
   print("Theta Rad:", theta_rad)

   greenwich_sidereal_time = theta_rad-(int(maal_360)*360)
   if greenwich_sidereal_time < 0:
      greenwich_sidereal_time = greenwich_sidereal_time + 360
   local_sidereal_time_deg = meteor['meteor']['end_point'][0]+greenwich_sidereal_time

   output['D21'] = local_sidereal_time_deg

   eastpoint['B52'] = JD_at_t
   eastpoint['C54'] = greenwich_sidereal_time
   eastpoint['R29'] = R29
   eastpoint['S29'] = S29

   # theta rad vars
   eastpoint['S34'] = T
   eastpoint['I48'] = T
   eastpoint['J48'] = t
   eastpoint['T34'] = theta_rad
   eastpoint['U34'] = maal_360

   input['C22'] = yr_cor
   input['D22'] = mon_cor
   input['E22'] = day
   input['C24'] = hour
   input['D24'] = min
   input['E24'] = sec

   return(input, eastpoint, output)

def earth_pos_vars(input, rekenmodule):

   ex,ey,ez,evx,evy,evz,evl = earth_position (input['mike']['input_date'])
   print()
   print(ex)
   print(ey)
   print(ez)
   print(evx)
   print(evy)
   print(evz)
   print()


   input['H17'] = ex
   input['I17'] = ey
   input['J17'] = ez
   input['H18'] = evx
   input['I18'] = evy
   input['J18'] = evz

   rekenmodule['A4'] = input['H17']
   rekenmodule['B4'] = input['I17']
   rekenmodule['C4'] = input['J17']
   d_earth_ecl = np.sqrt(ex**2+ey**2+ez**2)
   rekenmodule['D4'] = d_earth_ecl

   #V in x,y,z VxEarth, VyEarth, VzEarth, Va
   rekenmodule['F4'] = ((input['H18'])/(86400)*(rekenmodule['F1']*100000000))
   rekenmodule['G4'] = ((input['I18'])/(86400)*(rekenmodule['F1']*100000000))
   rekenmodule['H4'] = ((input['J18'])/(86400)*(rekenmodule['F1']*100000000))
   rekenmodule['I4'] = math.sqrt(rekenmodule['F4']**2+rekenmodule['G4']**2+rekenmodule['H4']**2)

   print("VyEarth:", rekenmodule['G4'] )

   #Vgeo needed for this one...
   #rekenmodule['F5'] = inputb['G13']

   return(input, rekenmodule)

def compute_observed_hour_angle(meteor,input,sheet2, output):

   # cos radiant el * sin radiant az / cos rad_dec


   print("OUT G21", output['G21'])
   sin_u = (-1*math.cos(math.radians(meteor['meteor']['rad_el']))*math.sin(math.radians(meteor['meteor']['rad_az'])))/math.cos(math.radians(output['G21']))

   sin_u_radians = math.asin(sin_u)
   sin_u_degrees = math.degrees(sin_u_radians)
   if sin_u_degrees < 0:
      sin_u_degrees = sin_u_degrees + 360

   print("SIN_U", sin_u)
   local_sidereal_hour_angle = sin_u_degrees
   output['E21'] = local_sidereal_hour_angle
   sheet2['F10'] = sin_u
   sheet2['G10'] = sin_u_radians
   sheet2['H10'] = sin_u_degrees
   sheet2['N10'] = local_sidereal_hour_angle

   # compute observed radiant RA from sidereal & hourangle
   output['F21'] = output['D21'] - local_sidereal_hour_angle

   print("REAL RA: ", output['F21'])
   if output['F21'] < 0:
      output['F21'] = output['F21'] + 360
   print("REAL RA: ", output['F21'])
   return(output, sheet2)

def eastpoint_vars_step1(eastpoint,input,output):
   eastpoint_el  = 0
   eastpoint_az = 90
   lat = input['D12']
   lon = input['C12']
   rad_ra = output['F21']
   rad_dec = output['G21']
   T = eastpoint['I48']
   t = eastpoint['J48']

   eastpoint['C18'] = eastpoint_az
   eastpoint['D18'] = eastpoint_el
   local_sidereal_time_deg = output['D26']
   eastpoint_sin_dec = math.sin(math.radians(eastpoint_el))*math.sin(math.radians(lat))+math.cos(math.radians(eastpoint_el))*math.cos(math.radians(eastpoint_az))*math.cos(math.radians(lat))
   eastpoint['K13'] = eastpoint_sin_dec

   eastpoint_sin_u = (-1*(math.cos(math.radians(eastpoint_el))*math.sin(math.radians(eastpoint_az))))/math.cos(math.radians(eastpoint_sin_dec))
   eastpoint_sin_u_rad = math.asin(eastpoint_sin_u)
   eastpoint_sin_u_deg = math.degrees(eastpoint_sin_u_rad)
   if eastpoint_sin_u_deg < 0:
      eastpoint_sin_u_deg = eastpoint_sin_u_deg + 360
   eastpoint_hour_angle = eastpoint_sin_u_deg

   eastpoint['O19'] = eastpoint_sin_u
   eastpoint['P19'] = eastpoint_sin_u_rad
   eastpoint['Q19'] = eastpoint_sin_u_deg
   eastpoint['W19'] = eastpoint_hour_angle

   eastpoint_sidereal_hour_diff = local_sidereal_time_deg - eastpoint_hour_angle
   eastpoint_epoch_ra = eastpoint_sidereal_hour_diff # epoch_RA
   eastpoint['E30'] = eastpoint_epoch_ra

   theta_arcsec=((2004.3109-(0.8533*T)-(0.000217*(T*T)))*t)-((0.42665+(0.000217*T))*(T*T))-(0.041833*(t*t*t))
   print("THETA ARCSEC:", theta_arcsec)
   theta_deg = (theta_arcsec/60)/60
   print("THETA DEG:", theta_deg)
   eastpoint['O49'] = theta_arcsec
   eastpoint['P49'] = theta_deg

   epoch = math.radians(rad_dec)
   eastpoint['H50'] = epoch
    
   print("H50:", eastpoint['H50'])

   zeta_arcsec = ((2306.2181+(1.39656*T)-(0.000139*(T*T)))*t)+((0.30188-(0.000344*T))*(t*t))+(0.017998*(t*t*t))
   zeta_deg = (zeta_arcsec/60)/60
   eastpoint['K49'] = zeta_arcsec
   eastpoint['L49'] = zeta_deg
   rad_ra = output['F21']
   print("RADRA:", output['F21'])

   #WRONG! 
   eastpoint['H49'] = math.radians(rad_ra+math.radians(zeta_deg))

   eastpoint['L49'] = zeta_deg
   eastpoint['L50'] = math.radians(zeta_deg)
   eastpoint['P50'] = math.radians(theta_deg)
   eastpoint['H50'] = math.radians(rad_dec)
   eastpoint['G50'] = rad_dec

   return(output, eastpoint)

def observed_radiant_to_j2000(input,eastpoint,output):
   rad_dec = output['G21']
   rad_ra = output['F21']
   theta_deg = eastpoint['P49']
   theta_deg_rad = eastpoint['P50']
   zeta_deg = eastpoint['L49']
   zeta_deg_rad = math.radians(eastpoint['L49'])
   eastpoint['G49'] = rad_ra
   eastpoint['L51'] = math.radians(rad_ra)+math.radians(zeta_deg) 
   L51 = eastpoint['L51']

   print("RAD DEC:", rad_dec)
   ORJ2_A = math.cos(math.radians(rad_dec))*math.sin(math.radians(rad_ra)+math.radians(zeta_deg))
   ORJ2_B = ( math.cos(math.radians(theta_deg)) * math.cos(math.radians(rad_dec)) * math.cos(math.radians(rad_ra+math.radians(zeta_deg))) -( math.sin(math.radians(theta_deg)) * math.sin(math.radians(rad_dec))))
   ORJ2_C = ( math.sin(math.radians(theta_deg)) * math.cos(math.radians(rad_dec)) * \
      math.cos(L51))+ \
      (math.cos(math.radians(theta_deg))* math.sin(math.radians(rad_dec)))

   print("ORJ2_A:", ORJ2_A)
   print("ORJ2_B:", ORJ2_B)
   print("ORJ2_C:", ORJ2_C)

   ra_min_z = math.atan2(ORJ2_A,ORJ2_B)
   print("RA MIN Z: ", ra_min_z)

   L54 = math.degrees(ra_min_z+math.radians(zeta_deg))
   #N54 = zeta_deg_rad + ra_min_z

   if L54 < 0:
      rad_raJ2 = L54 + 360
   else:
      rad_raJ2 = L54

   delta_rad = math.asin(ORJ2_C)
   delta_j2000 = math.degrees(delta_rad)
   print("Delta Rad:", delta_rad)
   print("Delta J2000:", delta_j2000)
   rad_decJ2 = delta_j2000
   print("J2000 RA/DEC :", rad_raJ2, rad_decJ2)
   output['H21'] = rad_raJ2
   output['I21'] = rad_decJ2
   return(output)

