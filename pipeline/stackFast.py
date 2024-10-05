import cv2
import json
import sys
import numpy as np
import os
import datetime 
from lib.PipeAutoCal import XYtoRADec
from lib.PipeUtil import load_json_file, save_json_file  
from Classes.AllSkyNetwork import AllSkyNetwork
from lib.Map import make_map, geo_intersec_point
from Classes.ImageClassifier import ImageClassifier
import glob
from Classes.Detector import Detector
import simplekml

def review_all_xy(indir):
    files = glob.glob(indir + "AMS57*-xy.json")
    for f in files:
        review_xy(f)

def review_xy(json_file):
    video_file = json_file.replace("-xy.json", ".mp4")
    video_fn = json_file.split("/")[-1].replace("-xy.json", ".mp4") 
    station_id, year, month, day, hour, min, sec,microsecond, cam_id = video_fn.split(".")[0].split("_")
    file_date = year + "-" + month + "-" + day + " " + hour + ":" + min + ":" + sec
    file_datetime = datetime.datetime.strptime(file_date, "%Y-%m-%d %H:%M:%S")
    cam_id = video_fn.split("_")[8].replace(".mp4", "")
    rfile = video_fn.replace(station_id + "_", "")
    med_frame = make_median_frame(video_file)
    cal_params, remote_json_conf,mask_img = ASN.get_remote_cal_params(station_id, cam_id, rfile, file_datetime,med_frame)
    # test center xy
    #print(json.dumps(cal_params, indent=4))
    print(video_file)
    if cal_params is not None:
        new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(1920/2,1080/2,rfile,cal_params,remote_json_conf)
        print("CENTER:", new_x, new_y, img_ra,img_dec, img_az, img_el)
        new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(1353,477,rfile,cal_params,remote_json_conf)
    data = load_json_file(json_file)
    frame_data = {}
    for row in data:
        oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = row
        frame_num = int(frame_num)
        if frame_num not in frame_data:
            frame_data[frame_num] = []
        frame_data[frame_num].append(row)
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file." + video_file)
    frames = []
    new_xy_data = []
    frame_num = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        if frame_num in frame_data:
            d = frame_data[frame_num]
            # loop over all objects in this frame
            txs = []
            tys = []
            for row in d:
                (oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point) = row
                if len(az_start_point) == 2:
                    slat, slon = az_start_point
                elif len(az_start_point) == 3:
                    slat, slon,salt = az_start_point
                
                img_x = x + int(w/2)
                img_y = y + int(h/2)
                txs.append(img_x)
                tys.append(img_y)
            if len(txs) > 1:
                tx = np.mean(txs)
                ty = np.mean(tys)
            else:
                tx = txs[0]
                ty = tys[0]
            if cal_params is not None:
                new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(tx,ty,rfile,cal_params,remote_json_conf)
                #az_end_point = point_at_distance(slat, slon, 0, float(img_az), float(img_el), 350*1000)
                az_end_point = calculate_new_location(slat, slon, 0, float(img_az), float(img_el), 350*1000)
            
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                label = str(oid) + " " + str(round(img_az,1)) + " " + str(round(img_el,1))
                cv2.putText(frame, str(label),  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
                new_xy_data.append((oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point))
                print("NEW DATA", oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point)
        cv2.imshow('img', frame)
        cv2.waitKey(30)
        frame_num += 1
    save_json_file(json_file, new_xy_data)
    print("Saved:", json_file)
    
import numpy as np
import math 

def calculate_new_location(lat, lon, alt, azimuth, elevation, distance):
    """
    Calculate a new geographic location based on starting point and projection parameters.
    
    :param lat: Starting latitude in degrees
    :param lon: Starting longitude in degrees
    :param alt: Starting altitude in meters
    :param azimuth: Azimuth angle in degrees (0 = North, 90 = East, 180 = South, 270 = West)
    :param elevation: Elevation angle in degrees (0 = horizontal, 90 = straight up)
    :param distance: Distance to project in meters
    :return: Tuple of (new_latitude, new_longitude, new_altitude)
    """
    # Convert latitude, longitude, azimuth, and elevation to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)

    # Earth's radius in meters (approximation)
    earth_radius = 6371000

    # Calculate the horizontal and vertical components of the distance
    horizontal_distance = distance * math.cos(elevation_rad)
    vertical_distance = distance * math.sin(elevation_rad)

    # Calculate the angular distance
    angular_distance = horizontal_distance / earth_radius

    # Calculate the new latitude
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(azimuth_rad)
    )

    # Calculate the new longitude
    new_lon_rad = lon_rad + math.atan2(
        math.sin(azimuth_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )

    # Calculate the new altitude
    new_alt = alt + vertical_distance

    # Convert new latitude and longitude back to degrees
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)

    return new_lat, new_lon, new_alt


def create_kmz(lines, points, filename='output.kmz'):
    kml = simplekml.Kml()
    new_lines = []
    new_points = []
    for s1,s2,s3, e1,e2,e3,color in lines:
        new_lines.append(((s2, s1,s3), (e2, e1,e3)))
    for l, ll, name in points:
        new_points.append((ll, l))
    print("LINES", new_lines)
    print("POINTS", new_points)
    # Add lines to the KML
    for line in new_lines:
        
        linestring = kml.newlinestring(coords=line)
        # set linestring relative to sea floor
        linestring.altitudemode = simplekml.AltitudeMode.relativetoground 
        
        linestring.style.linestyle.color = simplekml.Color.red  # Set line color
        linestring.style.linestyle.width = 5  # Set line width

    # Add points to the KML
    for point in new_points:
        pnt = kml.newpoint(coords=[(point[0], point[1])])  # Longitude, Latitude
        pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

    # Save as KMZ
    kml.savekmz(filename)
    print(f"Saved KMZ file as {filename}")

def stack_fast(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file." + video_file)
    frames = []
    stack = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if stack == None:
            stack = frame
        else:
            stack = np.maximum(stack, frame)
    cap.release()
    return stack 

def calculate_straightness(xs, ys):
    # Convert inputs to numpy arrays
    x = np.array(xs)
    y = np.array(ys)
    
    # Calculate the mean of x and y
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    # Calculate the terms needed for the numerator and denominator of R-squared
    numerator = np.sum((x - x_mean) * (y - y_mean)) ** 2
    denominator = np.sum((x - x_mean) ** 2) * np.sum((y - y_mean) ** 2)
    
    # Calculate R-squared
    r_squared = numerator / denominator
    
    return r_squared

def average_points(points):
    avg_x = 0
    avg_y = 0
    for point in points:
        avg_x += point[0]
        avg_y += point[1]
    avg_x = avg_x / len(points)
    avg_y = avg_y / len(points)
    return(avg_x, avg_y)

def add_padding(x1,y1,x2,y2, padding):
    x1 = x1 - padding
    y1 = y1 - padding
    x2 = x2 + padding
    y2 = y2 + padding
    if x1 < 0:
        x1 = 0
    if y1 < 0:
        y1 = 0
    if x2 > 1920:
        x2 = 1920
    if y2 > 1080:
        y2 = 1080
    return(x1,y1,x2,y2)

def object_to_roi(object, padding=5):
    xs = object['oxs']
    ys = object['oys']
    ws = object['ows']
    hs = object['ohs']
    x1 = min(xs) - 5
    y1 = min(ys) - 5
    x2 = max(xs) + 5
    y2 = max(ys) + 5
    if x1 < 0:
        x1 = 0
    if y1 < 0:
        y1 = 0
    if x2 > 1920:
        x2 = 1920
    if y2 > 1080:
        y2 = 1080
        
    return (x1,y1,x2,y2)

def object_to_center_xy(object):
    cxs = []
    cys = []
    for i in range(0, len(object['oxs'])):
        x = object['oxs'][i]
        y = object['oys'][i]
        w = object['ows'][i]
        h = object['ohs'][i]
        cx = x + (w/2)
        cy = y + (h/2)
        cxs.append(cx)
        cys.append(cy)
    return(cxs, cys)

def roi_resize(rx1, ry1, rx2, ry2, size):
    if size > 0:
        rx1, ry1, rx2, ry2 = rx1 - size , ry1 - size, rx2 + size, ry2 + size
    else:
        size = size * -1
        rx1, ry1, rx2, ry2 = rx1 + size , ry1 + size, rx2 - size, ry2 - size
    if rx1 < 0:
        rx1 = 0
    if ry1 < 0:
        ry1 = 0
    if rx2 > 1920:
        rx2 = 1920
    if ry2 > 1080:
        ry2 = 1080 
    return(rx1, ry1, rx2, ry2)

def channel_mask(track_objs, objects):
    
    
    c_mask = np.zeros((1080,1920,3),dtype=np.uint8)
    for obj_id in track_objs:
        print(obj_id)
        for i in range(0, len(objects[obj_id]['oxs'])):
            x = objects[obj_id]['oxs'][i]
            y = objects[obj_id]['oys'][i]
            w = objects[obj_id]['ows'][i]
            h = objects[obj_id]['ohs'][i]
            y1 = y 
            x1 = x 
            y2 = y+h
            x2 = x+w
            x1,y1,x2,y2 = add_padding(x1,y1,x2,y2, 20)
            c_mask[y1:y2,x1:x2] = 255,255,255
    # invert the mask
    c_mask = cv2.bitwise_not(c_mask)
    #cv2.imshow("mask", c_mask)
    #cv2.waitKey(0)
    return c_mask 
def reject_mask(track_objs, objects):
    # objs that are not tracked should be added to the mask
    r_mask = np.zeros((1080,1920,3),dtype=np.uint8)
    for obj_id in objects:
        if obj_id not in track_objs:
            x1, y1, x2, y2 = object_to_roi(objects[obj_id])
            print("MASK:", obj_id, x1, y1, x2, y2)
            r_mask[y1:y2,x1:x2] = 255,255,255
    # clear mask for our tracked objects
    for obj_id in track_objs:
        x1, y1, x2, y2 = object_to_roi(objects[obj_id])
        print("UNMASK:", obj_id, x1, y1, x2, y2)
        if x1 < 0:
            x1 = 0
        r_mask[y1:y2,x1:x2] = 0,0,0
    #cv2.imshow("mask", r_mask)
    #cv2.waitKey(0)
    return r_mask 
        
def review_object(obj_file):
    stack_file = obj_file.replace("-objects.json", "-stack.jpg")
    if os.path.exists(stack_file) is True:
        img = cv2.imread(stack_file)
        oimg = cv2.imread(stack_file)
    else:
        img = None
        
    obj_data = load_json_file(obj_file)
    track_obs = []
    temp = obj_data['track_obs'].split(",")
    for t in temp:
        track_obs.append(str(t))
    for obj_id in obj_data['objects']:
        if obj_id in track_obs:
            print("TRACKING:", obj_id)  
            color = (0,0,255)
        else:
            print("NOT TRACKING:", obj_id)
            color = (0,255,255)
        x1, y1, x2, y2 = object_to_roi(obj_data['objects'][obj_id])
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, str(obj_id),  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(img, str(obj_id),  (x1-2, y1-2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.imshow('img', img)
        if obj_id in track_obs:
            cv2.waitKey(30)
        else:
            cv2.waitKey(30)
    go = True 
    roi_plus = {}
    mimg = img.copy()
    while go is True:
        mimg = img.copy()
        cv2.imshow('img', mimg)
        key = cv2.waitKey(0)
        print("KEY:", key)
        if key == 27:
            go = False
        # + key increase ROI
        if key == 61:
            for oid in track_obs:
                print("INCREASE ROI for ", oid )
                if oid in roi_plus:
                    rx1, ry1, rx2, ry2 = roi_plus[oid] 
                else:
                    rx1, ry1, rx2, ry2 = object_to_roi(obj_data['objects'][oid])
                
                rx1, ry1, rx2, ry2 = roi_resize(rx1, ry1, rx2, ry2, 5)
                roi_plus[oid] = (rx1, ry1, rx2, ry2)
                print(rx1, ry1, rx2, ry2)
                cv2.rectangle(mimg, (rx1, ry1), (rx2, ry2), (255,255,255), 2)
                cv2.imshow('img', mimg)
                cv2.waitKey(30)
            cv2.imshow('img', mimg)
            cv2.waitKey(0)
            
        # - key decrease ROI
        if key == 45:
            for oid in track_obs:
                print("DECREASE ROI for", oid) 
                if oid in roi_plus:
                    rx1, ry1, rx2, ry2 = roi_plus[oid] 
                else:
                    rx1, ry1, rx2, ry2 = object_to_roi(obj_data['objects'][oid])
                rx1, ry1, rx2, ry2 = roi_resize(rx1, ry1, rx2, ry2, -5)
                roi_plus[oid] = (rx1, ry1, rx2, ry2)
                print("NEW ROI", rx1, ry1, rx2, ry2)
                cv2.rectangle(mimg, (rx1, ry1), (rx2, ry2), (255,255,255), 2)
                cv2.imshow('img', mimg)
                cv2.waitKey(30)
            
            cv2.imshow('img', mimg)
            cv2.waitKey(0)
        # r key reject object
        if key == 114:
            reject_obj_mask = channel_mask(track_obs, obj_data['objects']) 
            rmask_file = obj_file.replace("-objects.json", "-mask.jpg")
            cv2.imwrite(rmask_file, reject_obj_mask)
            print("Saved:", rmask_file)
            new_sub = cv2.subtract(mimg, reject_obj_mask)
            cv2.imshow('img', new_sub)
            cv2.waitKey(0)
            
        # t key re-track object
        if key == 116:
            print("Re-track object")
            retrack_obs(obj_file)
            
def retrack_obs(object_file):
    objects = {}
    video_file = object_file.replace("-objects.json", ".mp4")
    video_fn = video_file.split("/")[-1]
    stack_file = object_file.replace("-objects.json", "-stack.jpg")
    mask_file = object_file.replace("-objects.json", "-mask.jpg") 
    mask_img = cv2.imread(mask_file)
    file = video_file
    print(video_file.split(".")[0].split("_"))
    station_id, year, month, day, hour, min, sec,microsecond, cam_id = video_fn.split(".")[0].split("_")
    file_date = year + "-" + month + "-" + day + " " + hour + ":" + min + ":" + sec
    file_datetime = datetime.datetime.strptime(file_date, "%Y-%m-%d %H:%M:%S")
    cam_id = file.split("_")[8].replace(".mp4", "")
    rfile = file.replace(station_id + "_", "")
    med_frame = make_median_frame(video_file)
    cal_params, remote_json_conf,mask_img = ASN.get_remote_cal_params(station_id, cam_id, rfile, file_datetime,med_frame)
    stack, frame_data = reduce_xy(video_file, cal_params, remote_json_conf, mask_img, file_datetime)
    object_frame_data = []
    for row in frame_data:
        frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = row
        cx = x + (w/2)
        cy = y + (h/2)
        oid, objects = Detector.find_objects(frame_num,x,y,w,h,cx,cy,intensity,objects, 120)
        
        object_frame_data.append((oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point))
        print(oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point)
        cv2.rectangle(stack, (x, y), (x+w, y+h), (0, 0, 255), 2) 
    cv2.imshow('img', stack)    
    cv2.waitKey(0)
    

def review_objects(indir, date):
    files = glob.glob(indir + "*-objects.json")
    print(indir + "*-objects.json")
    for f in files:
        print(f)
        review_object(f)
    
def group_objects(filename, frame_data, img):
    show_img = img.copy()
    objects = {}
    object_frame_data = []
    for row in frame_data:
        frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = row
        cx = x + (w/2)
        cy = y + (h/2)
        oid, objects = Detector.find_objects(frame_num,x,y,w,h,cx,cy,intensity,objects, 120)
        object_frame_data.append((oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point))
        cv2.putText(show_img, str(oid),  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
        print(frame_num, oid, cx,cy)
        print("Total Objects", len(objects))
    for obj_id in objects:
        print("OBJECT:", obj_id)
        if len(objects[obj_id]['oxs']) < 5:
            continue
        cxs, cys = object_to_center_xy(objects[obj_id])
        straightness = calculate_straightness(cxs, cys)
        print("STRAIGHTNESS:", straightness)
        x1, y1, x2, y2 = object_to_roi(objects[obj_id])
        mx = int((x1 + x2) / 2)
        my = int((y1 + y2) / 2)
        if y1 > 500:
            cv2.putText(show_img, str(obj_id),  (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        else:
            cv2.putText(show_img, str(obj_id),  (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        if straightness < .5:
            print("NOT A STRAIGHT LINE")
            continue
        cv2.rectangle(show_img, (x1, y1), (x2, y2), (0, 255, 0), 2) 
    if img is not None:
        cv2.imshow('img', show_img)
        cv2.waitKey(30)
        track_objects = input("Which objects do you want to track? (space separated list): ") 
        obs_ids = track_objects.split(",")
        for oid in obs_ids:
            o = int(oid)
            x1, y1, x2, y2 = object_to_roi(objects[o])
            cv2.rectangle(show_img, (x1, y1), (x2, y2), (0, 255, 255), 2) 
            
            print("TRACKING:", oid)
            #status, report = Detector.analyze_object(objects[oid])
    #    status, report = Detector.analyze_object(objects[obj_id])
        cv2.imshow('img', show_img)
        cv2.waitKey(30)
    ofd = []
    for row in object_frame_data:
        oid, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = row
        if str(oid) in obs_ids:
            ofd.append(row) 
    return(track_objects, objects, ofd)

def obs_map(indir):
    files = glob.glob(indir + "*.json")
    color = [0,1,0,.25]
    stations = {}
    files = glob.glob(indir + "*xy.json")
    for f in files:
        lines = []
        points = []
        print(f)
        root_fn = f.split("/")[-1].replace("-xy.json", "")
        
        station_id = f.split("/")[-1].split("_")[0]
        if station_id not in stations:
            stations[station_id] = []
        frame_data = load_json_file(f)
        for row in frame_data:
            if len(row) == 11:
                oid, frame_time_str, x, y, w, h,ints, img_az, img_el, loc, az_end_point = row
            else:
                oid, fc, frame_time_str, x, y, w, h,ints, img_az, img_el, loc, az_end_point = row
            if az_end_point is not None:
                lines.append((loc[0], loc[1], 0, az_end_point[0], az_end_point[1], az_end_point[2], "green"))
            if len(stations[station_id]) == 0 and len(loc) != 0:
                stations[station_id] = loc 
        print(stations) 
        print(station_id)    
        if len(stations[station_id]) >= 2:
            points.append((stations[station_id][0], stations[station_id][1], station_id))
        kmz_file = indir + f"{root_fn}_OBS_MAP.kmz"
        create_kmz(lines, points, filename=kmz_file)
        print("Saved:", kmz_file)
    # make avg point from all points
    center_latlon = average_points(points)        
    #map_img = make_map(points, lines, center_latlon) 
    #cv2.imshow('map', map_img)
    #cv2.waitKey(0)
    
    

def obs_map_old(indir):
    files = glob.glob(indir + "*.json")
    lines = []
    points = []
    # kml color
    color = [0,1,0,.25]
    stations = {}
    for f in files:
        fn = f.split("/")[-1]
        root_file = fn.replace("-xy.json", "")
        stack_file = f.replace("-xy.json", "-stack.jpg")
        object_file = f.replace("-xy.json", "-objects.json")
        if os.path.exists(stack_file) is True:
            img = cv2.imread(stack_file)
        else:
            img = None
            print("NO stack file!", stack_file)
        jdata = load_json_file(f)
        # this is a bug here!
        if os.path.exists(object_file) is True:
            obj_data = load_json_file(object_file)
            track_obs = obj_data['track_obs'] 
            objects = obj_data['objects'] 
            object_frame_data = obj_data['object_frame_data'] 
        else:
            track_obs, objects, object_frame_data = group_objects(root_file, jdata, img)
            obj_data = {}
            obj_data['track_obs'] = track_obs
            obj_data['objects'] = objects 
            obj_data['object_frame_data'] = object_frame_data
        save_json_file(object_file, obj_data) 
        print("Saved", object_file)
        fn = f.split("/")[-1]
        station_id = fn.split("_")[0]
        fc = 0
        if station_id not in stations:
            stations[station_id] = []
        if len(object_frame_data) > 0:
            obj_id, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = object_frame_data[0] 
        else:
            continue
        if img_az is None:
            continue
        lines.append((az_start_point[0], az_start_point[1], 0, az_end_point[0], az_end_point[1], az_end_point[2], "green"))
        obj_id, frame_num, frame_time, x, y, w, h, intensity, img_az, img_el, az_start_point, az_end_point = object_frame_data[-1] 
        
        lines.append((az_start_point[0], az_start_point[1], 0, az_end_point[0], az_end_point[1], az_end_point[2], "green"))
        if len(stations[station_id]) == 0:
            stations[station_id] = az_start_point
    # now all stations are done
    for station_id in stations:
        print("STATION:", station_id, stations[station_id])
        if len(stations[station_id]) == 0:
            print("BAD STATION:", station_id)
            continue
        points.append((stations[station_id][0], stations[station_id][1], station_id))
    # make avg point from all points
    center_latlon = average_points(points)        
    #map_img = make_map(points, lines, center_latlon) 
    #cv2.imshow('map', map_img)
    #cv2.waitKey(0)
    
    cv2.imwrite(indir + "obs-map.jpg", map_img)
    
def load_mask(station_id, cam_id):
    local_mask_file = local_cal_dir + station_id + "_" + cam_id + "_mask.png"
    remote_mask_file = cloud_cal_dir + "MASKS/" + cam_id + "_mask.png"

    if os.path.exists(local_mask_file) is False:
        if os.path.exists(remote_mask_file) is True:
            cmd = "cp " + remote_mask_file + " " + local_mask_file
            os.system(cmd)
    if os.path.exists(local_mask_file) is True:
        mask_img = cv2.imread(local_mask_file)
        mask_img = cv2.resize(mask_img, (1920,1080))
    else:
        mask_img = np.zeros((1080,1920,3),dtype=np.uint8)

def make_median_frame(video_file):
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file." + video_file)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        if len(frames) > 10:
            break
    cap.release()
    med_frame = np.median(frames, axis=0).astype(dtype=np.uint8)
    return med_frame

def batch(indir, date):
    files = os.listdir(indir)
    for file in files:
        if "AMS249" not in file:
            continue
        if "mp4" in file:
            med_frame = make_median_frame(indir + file)
            stack_file = file.replace(".mp4", "-stack.jpg")
            json_file = file.replace(".mp4", "-xy.json")
            if os.path.exists(indir + json_file):
                print("Skip done")
                #continue
            station_id = file.split("_")[0]
            print(file.split("_"))
            station_id, year, month, day, hour, min, sec,microsecond, cam_id = file.split(".")[0].split("_")
            file_date = year + "-" + month + "-" + day + " " + hour + ":" + min + ":" + sec
            file_datetime = datetime.datetime.strptime(file_date, "%Y-%m-%d %H:%M:%S")
            cam_id = file.split("_")[8].replace(".mp4", "")
            rfile = file.replace(station_id + "_", "")
            print(station_id, cam_id, rfile, file_datetime)
            cal_params, remote_json_conf,mask_img = ASN.get_remote_cal_params(station_id, cam_id, rfile, file_datetime,med_frame)
            stack, frame_data = reduce_xy(indir + file, cal_params, remote_json_conf, mask_img, file_datetime)
            cv2.imwrite(indir + stack_file, stack) 
            with open(indir + json_file, 'w') as outfile:
                json.dump(frame_data, outfile) 
            print("Wrote JSON File:", json_file)
            
def find_best_thresh(img):
    checking = False
    if len(img.shape) == 3:
        bw = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        bw = img.copy()
        
    max_val = np.max(bw)
    threshhold = max_val * .9
    if threshhold < 50:
        threshhold = 50
        
    while checking is False:
        #print("THRESHOLD:", threshhold)
        thresh_img = cv2.threshold(bw, threshhold, 255, cv2.THRESH_BINARY)[1]
        #cv2.waitKey(0)
        #thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_BGR2GRAY)
        cnts = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        if len(cnts) > 5:
            threshold = threshhold + 10
        else:
            checking = True
        if threshhold > 100:
            checking = True
    return(threshhold)

def solve_objects(in_dir, event_id):
    object_file = in_dir + "object_data.json"
    objects = load_json_file(object_file)
    for obj_id in objects['objects']:
        status, report = Detector.analyze_object(objects['objects'][obj_id])
        x1, y1, x2, y2 = object_to_roi(objects['objects'][obj_id])
        if len(report['bad_items']) > 0:
            print("bad obj skip")    
        else:
            print("REPORT:", json.dumps(report,indent=4))


def frame_data_to_good_obs(in_dir, event_id):
    good_obs = {}
    bad_obs = []
    files = glob.glob(in_dir + "*-xy.json")
    for file in files:
        st_id = file.split("/")[-1].split("_")[0]
        fn = file.split("/")[-1]
        fn_no_site = fn.replace(st_id + "_", "")
        fn = fn_no_site
        if st_id not in good_obs:
            good_obs[st_id] = {}
        good_obs[st_id] = {}
        good_obs[st_id][fn] = {}
        good_obs[st_id][fn]['xs'] = []
        good_obs[st_id][fn]['ys'] = []
        good_obs[st_id][fn]['azs'] = []
        good_obs[st_id][fn]['els'] = []
        good_obs[st_id][fn]['ints'] = []
        good_obs[st_id][fn]['gc_azs'] = []
        good_obs[st_id][fn]['gc_els'] = []
        good_obs[st_id][fn]['times'] = []
        good_obs[st_id][fn]['fns'] = []
        good_obs[st_id][fn]['loc'] = []
        
        frame_data = load_json_file(file)    
        fdc = 0
        for row in frame_data:
            print(row)
            if len(row) == 11:
                oid, frame_time_str, x, y, w, h,ints, img_az, img_el, loc, az_end_point = row
            else:
                oid, fc, frame_time_str, x, y, w, h,ints, img_az, img_el, loc, az_end_point = row
            if len(good_obs[st_id][fn]['loc']) == 0:
                good_obs[st_id][fn]['loc'] = loc
                
            if w == 1 and h == 1:
                continue
            if img_az is None:
                continue
            # adjust for partial
            if az_end_point[2] < 1000:
                continue
            #if "AMS57" in file or "AMS58" in file or "AMS51" in file:
            if "AMS51" in file:
                continue
            if "19_31" in file or "19_30" in file:
            #if True:
                good_obs[st_id][fn]['fns'].append(fc)
                good_obs[st_id][fn]['times'].append(frame_time_str)
                good_obs[st_id][fn]['xs'].append(x)
                good_obs[st_id][fn]['ys'].append(y)
                good_obs[st_id][fn]['azs'].append(img_az)
                good_obs[st_id][fn]['els'].append(img_el)
                good_obs[st_id][fn]['ints'].append(ints)
                good_obs[st_id][fn]['gc_azs'].append(img_az)
                good_obs[st_id][fn]['gc_els'].append(img_el)
                print("GOOD", file)
            else:
                print("NOT GOOD", file)
                #input()
            fdc += 1
    save_json_file(f"{in_dir}{event_id}_GOOD_OBS.json", good_obs)    
    ev_dir = ASN.local_event_dir + ASN.year + "/" + ASN.month + "/" + ASN.day  + "/" + event_id + "/"
    if os.path.exists(ev_dir) is False:
        os.makedirs(ev_dir)
    save_json_file(f"{ev_dir}{event_id}_GOOD_OBS.json", good_obs)    

def reduce_xy(video_file, cal_params, json_conf, mask_img, file_datetime):
    objects = {}
    rmask_file = video_file.replace(".mp4", "-mask.jpg")
    if os.path.exists(rmask_file) is True:
        rmask = cv2.imread(rmask_file)
    else:
        rmask = None
    lvideo = video_file.split("/")[-1]
    station_id = lvideo.split("_")[0]
    print(station_id, video_file, lvideo)
    slat = float(json_conf['site']['device_lat'])
    slon = float(json_conf['site']['device_lng'])
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file." + video_file)
    stack = None
    sub = None
    fc = 0
    frame_data = []
    best_thresh = None
    extra_thresh = 0
    if rmask is not None:
        if rmask.shape[0] != 1080:
            rmask = cv2.resize(rmask, (1920,1080))
    else:
        print("NO MASK!", video_file)
        input("Continue")
    while True:
        ret, frame = cap.read()
        
        if frame is None:
            break
        if frame.shape[0] != 1080:
            frame = cv2.resize(frame, (1920,1080))
        # determine the frame time from the file datetime + the frame number at 25 fps
        frame_time = file_datetime + datetime.timedelta(seconds=fc/25)
        frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if rmask is not None:
            frame = cv2.subtract(frame, rmask)
        if mask_img.shape[0] != frame.shape[0]:
            mask_img = cv2.resize(mask_img, (frame.shape[1], frame.shape[0]))
        frame = cv2.subtract(frame, mask_img)
        if not ret:
            break
        if stack is not None:
            sub = cv2.subtract(frame, stack)
        if stack is None:
            stack = frame 
        else: 
            stack = np.maximum(stack, frame)
        if sub is not None:
            bw = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            if best_thresh is None:
                threshhold = find_best_thresh(bw)
                best_thresh = True 
            if threshhold < 10:
                threshhold = 10
            if threshhold > 10:
                threshhold = 10 
            cv2.imshow('img', frame)
            cv2.waitKey(30)
            thresh_img = cv2.threshold(sub, threshhold + extra_thresh, 255, cv2.THRESH_BINARY)[1]
            if len(thresh_img.shape) > 2:
                thresh_img = cv2.cvtColor(thresh_img, cv2.COLOR_BGR2GRAY)
            cnts = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            if len(cnts) > 5:
                extra_thresh += 10 
            cnts = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            marked = frame.copy()
            if len(cnts) > 0:
                for c in cnts:
                    x,y,w,h = cv2.boundingRect(c)
                    img_x = x + (w/2)
                    img_y = y + (h/2)
                    rvideo_file = video_file.split("/")[-1].replace(station_id + "_", "")
                    if cal_params is not None:
                        print("IMG/CAL", img_x, img_y, rvideo_file)
                        print("AZ/EL Center", cal_params['center_az'], cal_params['center_el'])
                        print("POS/PXS", cal_params['position_angle'], cal_params['pixscale'])
                        print(json_conf['site']['device_lat'], json_conf['site']['device_lng'], json_conf['site']['device_alt'])
                        new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,rvideo_file,cal_params,json_conf)
                        print("FILE", rvideo_file)
                        #az_end_point = ASN.find_point_from_az_dist(slat,slon,float(img_az),350)
                        #az_end_point = point_at_distance(slat, slon, 0, float(img_az), float(img_el), 350*1000)
                        az_end_point = calculate_new_location(slat, slon, 0, float(img_az), float(img_el), 350*1000)
                        print("RA/DEC/AZ/EL:", img_ra,img_dec, img_az, img_el, az_end_point)
                        img_az = round(float(img_az),3)  
                        img_el = round(float(img_el),3)  
                    else:
                        img_ra = None
                        img_dec = None
                        img_az = None
                        img_el = None
                        az_end_point = None
                        print("FAIL NO CAL FILE")
                    cv2.rectangle(marked, (x, y), (x + w, y + h), (36,255,12), 2)      
                    ints = int(np.sum(sub[y:y+h, x:x+w]))
                    # frame count, frame time, x, y, w,h,intensity, img_az, img_el, az_start_point, az_end_point
                    lat = json_conf['site']['device_lat']
                    lon = json_conf['site']['device_lng']
                    cx = x + (w/2)
                    cy = y + (h/2)
                    oid, objects = Detector.find_objects(fc,x,y,w,h,cx,cy,ints,objects, 120)
                    frame_data.append((oid, fc, frame_time_str, x, y, w, h,ints, img_az, img_el, [round(slat,3),round(slon,3)], az_end_point))
                    cv2.putText(marked, str(oid),  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
        
                cv2.imshow('img', marked)
                cv2.waitKey(10)
        fc += 1
        if fc % 100 == 0:
            print(fc) 
    cap.release()
    return stack, frame_data

def stackFast(video_file):
    
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        sys.exit("Error: Could not open video file " + video_file)
    stack = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if stack is None:
            stack = frame 
        else: 
            stack = np.maximum(stack, frame)
    cap.release()
    return stack

ROOT_DIR = "/mnt/f/AI/DATASETS/ALLSKY"
EXCEPTIONS_DIR = "/mnt/f/AI/DATASETS/ALLSKY/SOURCE/EXCEPTIONS"
MODEL_DIR = f"{ROOT_DIR}/MODELS"
time_of_day = "NIGHT"
dataset_volume = "MOVING_OBJECTS"
model_type = "RESNET101"
model_name = f"{dataset_volume}_{model_type}.pth"
model_path = f"{MODEL_DIR}/{model_name}"

if __name__ == "__main__":
    # cmd = stack or batch
    cmd = sys.argv[1]
    if cmd == "obs_map":
        indir = sys.argv[2]
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        obs_map(indir) 
    if cmd == "batch":
        indir = sys.argv[2]
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
    
        print(f"Loading model from {model_path}")
        classifier = ImageClassifier(model_path)
        batch(indir, date)
    if cmd == "solve_objects":
        # indir / date / event_id
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        frame_data_to_good_obs(sys.argv[2], sys.argv[4])
        #solve_objects(sys.argv[2], sys.argv[3])
    if cmd == "review_objects":
        # indir / event_id
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        review_objects(sys.argv[2], date)
        print("DONE")
    if cmd == "stack_fast":
        video_file = sys.argv[2]
        stack = stackFast(video_file)
        cv2.imwrite(video_file.replace(".mp4", "-stack.jpg"), stack)
        cv2.imshow('stack', stack)
        cv2.waitKey(0)
    if cmd == "review_all_xy":
        indir = sys.argv[2]
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        review_all_xy(indir)
        
    if cmd == "review_xy":
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        review_xy(sys.argv[2])
          
    if cmd == "stack":
        date = sys.argv[3]
        ASN = AllSkyNetwork()
        ASN.set_dates(date)
        video_file = sys.argv[2]
        video_fn = video_file.split("/")[-1]
        stack_file = video_file.replace(".mp4", "-stack.jpg")
         
        station_id, year, month, day, hour, min, sec,microsecond, cam_id = video_fn.split(".")[0].split("_")
        file_date = year + "-" + month + "-" + day + " " + hour + ":" + min + ":" + sec
        file_datetime = datetime.datetime.strptime(file_date, "%Y-%m-%d %H:%M:%S")
        cam_id = video_fn.split("_")[8].replace(".mp4", "")
        rfile = video_fn.replace(station_id + "_", "")
        med_frame = make_median_frame(video_file)
        cal_params, remote_json_conf,mask_img = ASN.get_remote_cal_params(station_id, cam_id, rfile, file_datetime,med_frame)
        
        stack, frame_data = reduce_xy(video_file, cal_params, remote_json_conf, mask_img, file_datetime)
        # save json
        json_file = video_file.replace(".mp4", "-xy.json")
        with open(json_file, 'w') as outfile:
            json.dump(frame_data, outfile) 
        print("JSON File:", json_file) 
        cv2.imshow('stack', stack)
        cv2.waitKey(0)
        cv2.destroyAllWindows
        cv2.imwrite(stack_file, stack) 
