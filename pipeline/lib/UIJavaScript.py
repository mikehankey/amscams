"""

JavaScript functions 
Style Sheets
HTML templates

for the UI

"""

JS_REJECT_METEOR = """

function reject_meteor(sd_video_file, div_id) {
   d1 = document.getElementById(div_id);

   del_div_id = div_id + "-del"
   SwapDivsWithClick(div_id,del_div_id,0)

   //d1.className = "deactive";
   //kd1.setAttribute("style","opacity:0.2; -moz-opacity:0.2; filter:alpha(opacity=20)");

}

"""

JS_SHOW_HIDE = """
   function show_hide(div_id) {
      var x = document.getElementById(div_id);
      if (x.style.display === "none") {
         x.style.display = "block";
      } else {
         x.style.display = "none";
      }
   }


"""

JS_SWAP_DIV_WITH_CLICK = """

// call : javascript:SwapDivsWithClick('div_id1','div_id2',play_vid)
function SwapDivsWithClick(div1,div2,play_vid)
{
   d1 = document.getElementById(div1);
   d2 = document.getElementById(div2);
   if (play_vid == 1) {
      div_vid = "video_" + div1
      vid = document.getElementById(div_vid)
      vid.play()
   }
   if( d2.style.display == "none" )
   {
      d1.style.display = "none";
      d2.style.display = "block";
   }
   else
   {
      d1.style.display = "block";
      d2.style.display = "none";
   }
}



"""

STYLE_IMAGE_OVERLAY = """

.header-title {
   float: left;
}
.header-links {
   float: right;
}

.breadcrumbs {
  padding: 10px 10px 0px 10px;
  float: left;
}

.header{
  padding: 0px 0px 0px 0px;
  width: 95%;
  margin: 0px 0px 0px 0px;
  overflow: hidden;
  border: 0px solid #000000;
}

.main {
  padding: 0px 25px 25px 25px;
  margin: auto;
  width: 100%;
  overflow: hidden;
}

.container {
  padding: 25px 25px 25px 25px;
  position: relative;
  float: left;
}


.image-deactive {
  opacity: .5;
  display: block;
  width: 320;
  height: 160;
  height: auto;
  transition: .5s ease;
  backface-visibility: hidden;
}


.image {
  opacity: 1;
  display: block;
  width: 320;
  height: 160;
  height: auto;
  transition: .5s ease;
  backface-visibility: hidden;
}

.middle {
  transition: .5s ease;
  opacity: 0;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  -ms-transform: translate(-50%, -50%);
  text-align: center;
}

.deactive {
  transition: .5s ease;
  opacity: 50;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  -ms-transform: translate(-50%, -50%);
  text-align: center;
}


.container:hover .image {
  opacity: 0.5;
}

.container:hover .middle {
  opacity: .5;
}

.text {
  color: white;
  font-size: 12px;
  padding: 5px 5px;
  font-family: "Lucida Console, Courier, monospace";
}

"""

HTML_HEADER = """
<html>
<title>%TITLE%</title>
"""


HTML_FOOTER = """
</html>
"""
