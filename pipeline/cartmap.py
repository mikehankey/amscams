#!/usr/bin/python3
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.offsetbox import AnchoredText
from matplotlib.transforms import offset_copy
from lib.PipeUtil import load_json_file,save_json_file,cfe
import math
import numpy as np
from lib.PipeSolve import simple_solve

def point_from_bearing(p1, brng, d):
    lon1, lat1 = p1
    print("START:", p1)
    print("HEADING:", brng)
    print("DISTANCE:", d)
    brng = math.radians(brng)
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    R = 6378.1 #Radius of the Earth
    # brng = 1.57 #Bearing is 90 degrees converted to radians.
    # d = 15 #Distance in km
    lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
       math.cos(lat1)*math.sin(d/R)*math.cos(brng))
    lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)
    print("END:", lon2,lat2)
    return(lon2,lat2)

def main(meteor_file):
    mj = load_json_file(meteor_file)
    map_file = meteor_file.replace(".json", "-map.png")
    json_conf = load_json_file("../conf/as6.json")
    nsinfo = load_json_file("../conf/network_station_info.json")
    mse = mj['multi_station_event']
    station_points = []
    obs_lines = []
    obs = []
    fn, dir = fn_dir(meteor_file)
    day = fn[0:10]
    for i in range(0,len(mse['stations'])):
       event_id =  mse['event_id']
       print("EV", mse['event_id'])
       station = mse['stations'][i]
       station_lat,station_lon,station_alt = nsinfo[mse['stations'][i]]['loc']
       station_lat,station_lon,station_alt = float(station_lat),float(station_lon),float(station_alt)
       station_points.append((float(station_lon),float(station_lat),"green", station))
       if "meteor_frame_data" in mse['mfds'][i]:
          start_az = mse['mfds'][i]['meteor_frame_data'][0][9]
          end_az = mse['mfds'][i]['meteor_frame_data'][-1][9]
          start_el = mse['mfds'][i]['meteor_frame_data'][0][10]
          end_el = mse['mfds'][i]['meteor_frame_data'][-1][10]
          print(station,station_lat,station_lon, start_az,end_az,start_el,end_el) 
          start_lon2,start_lat2 = point_from_bearing((station_lon,station_lat), start_az, 250)
          end_lon2,end_lat2 = point_from_bearing((station_lon,station_lat), end_az, 250)
          #obs_lines.append(((float(station_lon),float(station_lat)), (float(start_lon2),float(start_lat2)),'red',''))
          #obs_lines.append(((float(station_lon),float(station_lat)), (float(end_lon2),float(end_lat2)),'green',''))

       else:
          print(station,station_lat,station_lon,"pending") 
    for key in mse:
        print(key)    

    sol_c_lat = []
    sol_c_lon = []
    solutions = simple_solve(day, event_id, json_conf)
    mj['solutions'] = solutions
    save_json_file(meteor_file,mj)
    color_pairs = [
       ["green", "red"],
       ["blue", "orange"]
    ]
    cp = 0
    for sol in solutions:
        print("SOLUTION:", sol)
        station_key, start_lat,start_lon,start_alt,end_lat,end_lon,end_alt,dist,dur,vel = sol
        sol_c_lat.append(start_lat)
        sol_c_lon.append(start_lon)
        sol_c_lat.append(end_lat)
        sol_c_lon.append(end_lon)
        print("DIST:", dist, dur, vel)
        obs_lines.append(((float(start_lon),float(start_lat)), (float(end_lon),float(end_lat)),'black',3,''))

        for i in range(0,len(mse['stations'])):
           station = mse['stations'][i]
           station_lat,station_lon,station_alt = nsinfo[mse['stations'][i]]['loc']
           station_lat,station_lon,station_alt = float(station_lat),float(station_lon),float(station_alt)
           print("CP:", color_pairs[cp])
           obs_lines.append(((float(station_lon),float(station_lat)), (float(start_lon),float(start_lat)),color_pairs[cp][1],1,''))
           obs_lines.append(((float(station_lon),float(station_lat)), (float(end_lon),float(end_lat)),color_pairs[cp][0],1,''))
           cp += 1
           if cp >= len(color_pairs):
              cp = 0

    # set area min_lon, max_lon, min_lat, max_lat
    #extent = [-70,-85,35,45]
    # points lon, lat, color, label 
    points = station_points
    lines = obs_lines

    elons = []
    elats = []
    for data in points :
       elons.append(data[0])
       elats.append(data[1])
    for data in lines :
       
       elons.append(data[1][0])
       elats.append(data[1][1])

    clon = np.mean(elons)
    clat = np.mean(elats)

    extent = [clon-2,clon+2,clat-2,clat+2]

    if len(solutions) > 1:
       ctlon = np.mean(sol_c_lon)
       ctlat = np.mean(sol_c_lat)

       extent2 = [ctlon-.5,ctlon+.5,ctlat-.5,ctlat+.5]
    else:
       extent2 = extent
    print("ELON:", elons)
    print("ELAT:", elats)
    print("AVG:", clon,clat)
    print("EXT:", extent)
    fig = plt.figure(figsize=(8,4.5))
    ax1 = fig.add_subplot(1, 2, 1, projection=ccrs.PlateCarree())
    ax1.set_extent(extent, crs=ccrs.PlateCarree())

    ax2 = fig.add_subplot(1, 2, 2, projection=ccrs.PlateCarree())

    ax1.margins(x=.1,y=.1)
    ax2.margins(x=.1,y=.1)

    print("EXTENT2 :", extent2)
    ax2.set_extent(extent2, crs=ccrs.PlateCarree())
    # Put a background image on for nice sea rendering.
    #ax.stock_img()

    # Create a feature for States/Admin 1 regions at 1:50m from Natural Earth
    states_provinces = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='50m',
        facecolor='none')

    SOURCE = 'Natural Earth'
    LICENSE = 'public domain'

    ax1.add_feature(cfeature.LAND)
    ax1.add_feature(cfeature.OCEAN)
    ax1.add_feature(cfeature.COASTLINE)
    ax1.add_feature(cfeature.BORDERS)
    ax1.add_feature(cfeature.LAKES)
    ax1.add_feature(cfeature.RIVERS)
    ax1.add_feature(states_provinces, edgecolor='gray')

    ax2.add_feature(cfeature.LAND)
    ax2.add_feature(cfeature.OCEAN)
    ax2.add_feature(cfeature.COASTLINE)
    ax2.add_feature(cfeature.BORDERS)
    ax2.add_feature(cfeature.LAKES)
    ax2.add_feature(cfeature.RIVERS)
    ax2.add_feature(states_provinces, edgecolor='gray')


    geodetic_transform = ccrs.Geodetic()._as_mpl_transform(ax1)
    text_transform = offset_copy(geodetic_transform, units='dots', x=+15)

    geodetic_transform2 = ccrs.Geodetic()._as_mpl_transform(ax2)


    # plot points
    for point in points:
       lon,lat,color,label = point
       ax1.plot(lon, lat, marker='o', color=color, markersize=5,
          alpha=0.7, transform=ccrs.Geodetic()) 
       ax1.text(lon, lat, label,
            verticalalignment='center', horizontalalignment='left',
            transform=text_transform,
            bbox=dict(facecolor='sandybrown', alpha=0.5, boxstyle='round'))
    # plot lines
    for line in lines:
       (p1,p2,color,thickness,label) = line
       slon,slat = p1
       elon,elat = p2

       ax1.plot([slon, elon], [slat, elat],
         color=color, linewidth=thickness, marker='o', markersize=3,
         # Be explicit about which transform you want:
         transform=geodetic_transform)
       #if color == 'black':
       if True:
          ax2.plot([slon, elon], [slat, elat],
             color=color, linewidth=thickness, marker='o', markersize=3,
             # Be explicit about which transform you want:
             transform=geodetic_transform2)
       if label != '':
           ax1.text(elon, elat, label,
               verticalalignment='center', horizontalalignment='left',
               transform=text_transform,
               bbox=dict(facecolor='sandybrown', alpha=0.5, boxstyle='round'))

    # Add a text annotation for the license information to the
    # the bottom right corner.
    text = AnchoredText(r'$\mathcircled{{c}}$ {}; license: {}'
                        ''.format(SOURCE, LICENSE),
                        loc=4, prop={'size': 12}, frameon=True)
    #ax.add_artist(text)
    plt.savefig(map_file)
    map_jpg = map_file.replace(".png", ".jpg")
    os.system("convert -resize 848x480 " + map_file + " " + map_jpg)
    os.system("rm " + map_file )

    print("saved:", map_file)
    #plt.show()

def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)


if __name__ == '__main__':
    main(sys.argv[1])
