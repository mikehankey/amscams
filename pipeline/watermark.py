
from PIL import ImageFont, ImageDraw, Image, ImageChops
import sys
img_file = sys.argv[1]
watermark = Image.open("ALLSKY_LOGO.png")
img = Image.open(img_file)
pw, ph = img.size

basewidth,baseheight = img.size
wpercent = (basewidth / float(watermark.size[0]))
hsize = int((float(img.size[1]) * float(wpercent)))

watermark = watermark.resize((basewidth, hsize), Image.Resampling.LANCZOS)
watermark.show()


#photo.paste(watermark,(0,0),watermark)
#photo.show()
