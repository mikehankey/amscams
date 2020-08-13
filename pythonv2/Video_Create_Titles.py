from lib.Video_Title_cv import *   



if __name__ == "__main__":
 
   #_title = input("Enter the title of the video: ")
   #_credits = input("Enter the music credits:")
   _color = (255,255,255,255) # Optional - it's white by default
   _with_line_animation = True # Optional - it's True by default
   _output_path = '/mnt/ams2/vid.mp4'
   #create_title_video(_title,_credits,_output_path,_color,_with_line_animation)


   _title = "Visit Allskycams.com"
   _subtitle = "for more information about our all sky cameras"
   _duration = 125 # In frames at 25fps
   _output_path =  '/mnt/ams2/allskycams.mp4'

   create_allskycams_video(_title,_subtitle,_duration,_output_path)

# IF YOU WANT TO CREATE A TITLE VIDEO 
# WITH
# 1 - THE AMS LOGO 
# 2 - A sequence with Title and credits:
_title = "BEST OF PERSEIDS 2020"
_credits = "Music by Naked Jungle - nakedjungle.bandcamp.com"

_color = (255,255,255,255) # Optional - it's white by default
_with_line_animation = True # Optional - it's True by default

#create_title_video(_title,_credits,_output_path,_color,_with_line_animation)

# IF YOU WANT TO CREATE A VIDEO TO THANKS THE OPERATORS:
# _operators = ['Mike Hankey','Vincent Perlerin','Marcel Duchamp','The Beatles']
# _duration = 125 # In frames at 25fps
# _output_path =  '/mnt/ams2/operator_credits.mp4'
# _with_line_animation = True # Optional - it's True by default
# _line_height = 45 # Optional - it's 45 by default, it works well with <=12 operators (one per line)
# _operator_font_size = 30 # Optional - it's 30 by default, it works well with <=12 operators (one per line)

# create_thank_operator_video(_operators, _duration, _output_path,_with_line_animation,_line_height,_operator_font_size)

# # IF YOU WANT TO CREATE A "VISIT ALLSKYCAMS video"
# _title = "Visit Allskycams.com"
# _subtitle = "for more information about our all sky cameras"
# _duration = 125 # In frames at 25fps
# _output_path =  '/mnt/ams2/allskycams.mp4'

# create_allskycams_video(_title,_subtitle,_duration,_output_path)