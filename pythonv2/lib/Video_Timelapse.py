from lib.Video_Tools import * 
 
#Generate Timelapse
def generate_timelapse(cam_id,date,fps,dim,text_pos,wat_pos, enhancement=0): 
    #frames are SD if HD are not found
    frames, path = get_hd_frames(camID,date)
    if(frames is None):
        print('NO FRAME FOUND')
        return ''
    else:
        where_path = add_info_to_frames(frames, path, date, camID, dim, text_pos,wat_pos,enhancement)
        return create_vid_from_frames(frames, where_path, date, camID,fps)
        