from lib.Video_Title_cv import *   


# IF YOU WANT TO CREATE A TITLE VIDEO 
# WITH
# 1 - THE AMS LOGO 
# 2 - A sequence with Title and credits:
_title = "BEST OF PERSEIDS 2019"
_credits = "Music by Naked Jungle - nakedjungle.bandcamp.com"
_output_path = '/mnt/ams2/vid.mp4'
_color = (255,255,255,255) # Optional - it's white by default
_with_line_animation = True # Optional - it's True by default

create_title_video(_title,_credits,_output_path,_color,_with_line_animation)

# IF YOU WANT TO CREATE A VIDEO TO THANKS THE OPERATORS:
_operators = ['Mike Hankey','Vincent Perlerin','Marcel Duchamp','The Beatles']
_duration = 125 # In frames at 25fps
_output_path =  '/mnt/ams2/operator_credits.mp4'

create_thank_operator_video(_operators, _duration, _output_path)

# IF YOU WANT TO CREATE A "VISIT ALLSKYCAMS video"
_title = "Visit Allskycams.com"
_subtitle = "for more information about our all sky cameras"
_duration = 125 # In frames at 25fps
_output_path =  '/mnt/ams2/allskycams.mp4'

create_allskycams_video(_title,_subtitle,_duration,_output_path)