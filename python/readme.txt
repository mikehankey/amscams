AMS/CAMS PYTHON FILES 
---------------------
* ffmpeg_record.py - Started with cron, records all video streams. 
* parse-motion.py - Reads motion.txt for a clip and then trims the unique events (and also grabs HD version of same)
   (todo): add confirmation file for actual meteors;
           add HD linker & trim after confirm
           add CAMS Analyzer after confirm
         
* process_data.py - Processes the incoming data and runs the CAMS thumbnailer and simple detector
camera-settingsv1.py - Camera settings script for version 1 cameras 
move-files.py - Script to delete older files and keep disk from filling up 
reject-filters.py - Checks all initial trim files (detected by pixel flux in thumbnailer), for motion or common types of false detections
pycgi/cams-viewer.py - Script to delete older files and keep disk from filling up 

util/camera-defaultsv1.py - Camera Defaults script for version 1 cameras 
util/rename-old-file-for-cams.py - Util script to convert old naming conventions to CAMS naming 

