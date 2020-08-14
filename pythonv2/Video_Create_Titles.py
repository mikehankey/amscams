import sys
from lib.Video_Title_cv import *   
from datetime import datetime


if __name__ == "__main__":
    
   if(len(sys.argv)>1):
      cmd = sys.argv[1] 

   if(cmd=="main_title"):
 
      _title   = input("Enter main title: ") or "BEST OF PERSEIDS " . str(datetime.now().year)
      _credits = input("Enter subtitle:")
      _color   = (255,255,255,255) # Optional - it's white by default
      _with_ams_logo_animation   = False
      _with_line_animation       = True # Optional - it's True by default
      _output_path = '/mnt/ams2/vid.mp4'
      print("Creating the video...")
      create_title_video(_title,_credits,_output_path,_color,_with_ams_logo_animation,_with_line_animation)
      print("FILE CREATED: /mnt/ams2/vid.mp4")

   elif(cmd=="title"):
      _title   = input("Enter main title: ") 
      _subtitle = input("Enter subtitle:")
      _output_path = '/mnt/ams2/title.mp4'  
      print("Creating the video...")
      create_simple_title_video(_title,_subtitle,_output_path)
      print("FILE CREATED: /mnt/ams2/vid.mp4")


   elif(cmd=='allskycams'):

      _title         = "Visit Allskycams.com"
      _subtitle      = "for more information about our all sky cameras"
      _duration      = input("Enter duration in seconds:")
      _duration      = int(duration)*25 #In frames at 25fps
      _output_path   =  '/mnt/ams2/allskycams.mp4'
      create_allskycams_video(_title,_subtitle,_duration,_output_path)
      print("FILE CREATED: /mnt/ams2/allskycams.mp4")

   
   elif(cmd== 'operators'):

      # IF YOU WANT TO CREATE A VIDEO TO THANKS THE OPERATORS:
      _operators = input("Enter each operator separated by a comma: ") 
      _operators = _operators.split(',')
      _duration = 125 # In frames at 25fps
      _output_path =  '/mnt/ams2/operator_credits.mp4'
      _with_line_animation = True # Optional - it's True by default
      _line_height = 45 # Optional - it's 45 by default, it works well with <=12 operators (one per line)
      _operator_font_size = 30 # Optional - it's 30 by default, it works well with <=12 operators (one per line)

      create_thank_operator_video(_operators, _duration, _output_path,_with_line_animation,_line_height,_operator_font_size)

   # # IF YOU WANT TO CREATE A "VISIT ALLSKYCAMS video"
   # _title = "Visit Allskycams.com"
   # _subtitle = "for more information about our all sky cameras"
   # _duration = 125 # In frames at 25fps
   # _output_path =  '/mnt/ams2/allskycams.mp4'

   # create_allskycams_video(_title,_subtitle,_duration,_output_path)