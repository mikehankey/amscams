
def get_meteor_date(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + ":" + fn[4] + ":" + fn[5]

def get_meteor_time(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[3] + ":" + fn[4] + ":" + fn[5]

def get_date_from_file(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',3)
	return fn[0] + "/" + fn[1] + "/" + fn[2]

def get_custom_video_date_and_cam_id(file):
	fn = file.split("/")[-1] 
	fn = fn.split("_")
	cam = fn[3].split(".")
	return (fn[0]+'/'+fn[1]+'/'+fn[2],cam[0])