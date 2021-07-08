from Classes.CloudCal import CloudCal
import sys
import os


if __name__ == "__main__":
   station_id = sys.argv[1]
   cam_id = sys.argv[2]
   CC = CloudCal(station_id = station_id, cam_id = cam_id)
   CC.refit_fovs()
   #CC.make_star_db()
