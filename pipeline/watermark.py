
from PIL import ImageFont, ImageDraw, Image, ImageChops

watermark = Image.open("ALLSKY_LOGO.png")
img = Image.open("/mnt/ams2/latest/AMS1_010004.jpg")
pw, ph = img.size

basewidth,baseheight = img.size
wpercent = (basewidth / float(watermark.size[0]))
hsize = int((float(img.size[1]) * float(wpercent)))

watermark = watermark.resize((basewidth, hsize), Image.ANTIALIAS)
watermark.show()


#photo.paste(watermark,(0,0),watermark)
#photo.show()
