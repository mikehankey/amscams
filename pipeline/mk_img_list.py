import os
import cv2
# make image list and slide show

def get_file_contents(file_name):
   fp = open(file_name)
   lines = ""
   for line in fp:
      lines += line
   return(lines)


# make image list and slide show
idir = "/mnt/ams2/AI/DATASETS/EXPORT/AMS1_FIREBALL_METEORS/"
css = get_file_contents("slideshow.css")
files = os.listdir(idir)
im_list = ""
slide = """
<div class="slideshow-container" style="border: 1px #000000 solid">
"""

tot = len(files)
c = 1
for f in sorted(files):
   if "jpg" not in f:
      continue
   im_list += "<a href={:s}>{:s}</a><br>".format(f, f)
   num_text = str(c) + " / " + str(tot)
   #print(idir + f)
   img = cv2.imread(idir + f) 
   h,w = img.shape[:2]
   #w = 1920 
   #h = 1080 

   slide += """
      <div class="mySlides fade">
         <div class="numbertext">{:s}</div>
            <img src="{:s}" style="width: {:s}px; height: {:s}px;">
         <div class="text">{:s}</div>
      </div>
   """.format(num_text, f, str(w), str(h), f)
   c += 1

slide += """
  <!-- Next and previous buttons -->
  <a class="prev" onclick="plusSlides(-1)">&#10094;</a>
  <a class="next" onclick="plusSlides(1)">&#10095;</a>
</div>
<br>

<!-- The dots/circles -->
<div style="text-align:center">
  <span class="dot" onclick="currentSlide(1)"></span>
  <span class="dot" onclick="currentSlide(2)"></span>
  <span class="dot" onclick="currentSlide(3)"></span>
</div>
"""
print("<style>")
print(css)
print("</style>")
print(slide)
print("""
<script>
let slideIndex = 1;
showSlides(slideIndex);

// Next/previous controls
function plusSlides(n) {
  showSlides(slideIndex += n);
}

// Thumbnail image controls
function currentSlide(n) {
  showSlides(slideIndex = n);
}

function showSlides(n) {
  let i;
  let slides = document.getElementsByClassName("mySlides");
  let dots = document.getElementsByClassName("dot");
  if (n > slides.length) {slideIndex = 1}
  if (n < 1) {slideIndex = slides.length}
  for (i = 0; i < slides.length; i++) {
    slides[i].style.display = "none";
  }
  for (i = 0; i < dots.length; i++) {
    dots[i].className = dots[i].className.replace(" active", "");
  }
  slides[slideIndex-1].style.display = "block";
  dots[slideIndex-1].className += " active";
}
</script>

        """)
