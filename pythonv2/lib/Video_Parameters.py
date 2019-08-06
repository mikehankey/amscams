import cgitb
from lib.VIDEO_VARS import * 
from pathlib import Path
from os.path import isfile, join, exists
from lib.FileIO import load_json_file, save_json_file
from lib.Get_Operator_info import get_operator_info
 

def get_video_job_default_parameters():
    #Create JSON file if it doesn't exist yet 
    js_file = Path(DEFAULT_VIDEO_PARAM)
    if js_file.is_file()== False: 
        f= open(DEFAULT_VIDEO_PARAM,"w+")

        #Get Operator Info
        operator = get_operator_info()
        operator_info = operator['name'] + ', ' + operator['obs_name']+ ', ' + operator['city'] + ', ' + operator['state']+ ', ' + operator['country']

        file.write('{"param": {"fps":'+ D_FPS+', "extra_logo": '+D_EXTRA_LOGO+', "wat_pos":'+ D_AMS_LOGO_POS +', "text_pos":'+D_CAM_INFO_POS+', "logo_pos":'+D_CUS_LOGO_POS+', "extra_text":'+  operator_info + '}}')
        f.close()
    return False