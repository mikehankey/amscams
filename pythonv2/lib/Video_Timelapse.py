from lib.Video_Tools import * 
 
 
#Generate Timelapse
def generate_timelapse(cam_id,date,start_date,end_date,fps,dim,text_pos,wat_pos,extra_text,logo,logo_pos,blend_sd,enhancement=0): 

    # First we tried width the HD Frames generated from the CRON
    frames, path  = get_hd_frames_from_HD_repo(cam_id,date,start_date,end_date,blend_sd)

    # Well... we have to deal with SD
    if(frames is None):
        #frames are SD if HD are not found
        frames, path = get_hd_frames(cam_id,date,start_date,end_date)

    if(frames is None):
        print('NO FRAME FOUND')
        return ''
    else:
        where_path = add_info_to_frames(frames, path, date, cam_id, extra_text, logo,logo_pos,dim, text_pos,wat_pos,enhancement)
        return create_vid_from_frames(frames, where_path, date, cam_id,fps,"jpg")
        