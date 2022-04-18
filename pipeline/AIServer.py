from flask import Flask
from lib.asciiart import *
app = Flask(__name__)
from random import randrange

from Classes.ASAI import AllSkyAI

ASAI = AllSkyAI()
ASAI.load_all_models()

#res = ASAI.meteor_yn(root_fn,roi_file,oimg,roi)


@app.route('/')
def hello():
    rand_num = randrange(4) 
    out = "<pre>" + ai_logo[rand_num] + "</pre>"

    out += """
    <pre>
       ALLSKY AI IMAGE CLASSIFIER USEAGE INSTRUCTIONS 
       ----------------------------------------------  
       http://YOUR_AS7_HOST_IP_OR_NAME:5000/AI/[COMMAND]/?variable=value

       SUPPORTED COMMANDS
       ------------------

       METEOR_ROI
           Use this API to determine if a cropped ROI image contains a meteor or something else. API returns
           YN confidence values for meteor, fireball and a multi-class identifier contain 12+ sky objects (planes, 
           birds, clouds, stars etc).

           input variables
           ---------------
           file            must be full qualified path to an ROI image already cropped and saved on the system.
                           image should be 224x244 from a 1920x1080 src image centered around the brightest point
                           of the object of interest. The entire object does not have to be inside the ROI image.
                           The model has been scaled around 1080p images, for best results upscale to this resolution
                           before making ROI image. 

           output variables
           ----------------
           meteor_yn       float value 0-100 represent the percent confidence the ROI image provide IS a meteor
           fireball_yn     float value 0-100 represent the percent confidence the ROI image provide IS a meteor
           mc_class        string value representing the object class [meteor, plane, bird etc] based on current allsky ai model
           mc_class_conf   float value 0-100 represent the percent confidence the ROI image provide IS the mc_class

           example usage         
           ----------------
           http://192.168.1.4:5000/AI/METEOR_ROI?file=/mnt/ams2/test_ai_roi_224.jpg 
             
       METEOR_OBJECT_SCAN 
           Pass an image of the sky into this API and it will identify the top 10 brighest objects based 
           on the ASTRONOMY NIGHTTIME ALLSKY AI models.  

           input variables
           ---------------
           file            should be a full image of any dimension. 

           output variables
           ----------------
           objects         array containing 2 elements. The first is the meteor_yn confidence percentage
                           the second is a 4 value ROI array containing the pixel location in the src image. 

           example usage         
           ----------------
           http://192.168.1.4:5000/AI/METEOR_OBJECT_SCAN?file=/mnt/ams2/test_ai_stack_image.jpg 

       WEATHER_ROI 
           Use this API to determine the weather status of a cropped ROI image. 

           input variables
           ---------------
           file     must be full qualified path to an ROI image already cropped and saved on the system
                    image can be a any size as long as it is a square shape with equal width and height. 

           example usage         
           ----------------
           http://192.168.1.4:5000/AI/WEATHER_ROI?file=/mnt/ams2/test_ai_roi_224.jpg 

       WEATHER_SCAN
           Use this API to determine the weather status of a 1080p image overall. 

           input variables
           ---------------
           file            must be full qualified path to an ROI image already cropped and saved on the system.
                           image should be 224x244 from a 1920x1080 src image centered around the brightest point
                           of the object of interest. The entire object does not have to be inside the ROI image.
                           The model has been scaled around 1080p images, for best results upscale to this resolution
                           before making ROI image. 

           example usage         
           ----------------
           http://192.168.1.4:5000/AI/WEATHER_SCAN?file=/mnt/ams2/test_ai_roi_224.jpg 
            
        
 
       

    </pre>

    """
    return out

# main driver function
if __name__ == '__main__':
  
    # run() method of Flask class runs the application 
    # on the local development server.
    app.run(host="0.0.0.0")
