
def get_meteor_date(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + ":" + fn[4] + ":" + fn[5]


def get_date_from_file(file)
	fn = file.split("/")[-1] 
	fn = fn.split('_',3)
	return fn[0] + "/" + fn[1] + "/" + fn[2]