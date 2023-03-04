import base64
import sys

def b64_encode_image(image_file):
   with open(image_file, "rb") as img_file:
      b64_string = base64.b64encode(img_file.read())
   print(b64_string)
   return(b64_string)

if __name__ == "__main__":
   b64_img = b64_encode_image(sys.argv[1])
