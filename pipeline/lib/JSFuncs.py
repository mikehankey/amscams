def video_preview_html_js(video_urls):
   text_vars = ""
   for url in video_urls:
      if text_vars != "":
         text_vars += ",\n"
      text_vars += """'{:s}'""".format(url)

   js = """
   <div id="videoContainer" style="display:inline-block"></div>
   <b id="output" style="vertical-align:top"></b>
   <script>
   var videoContainer = document.getElementById('videoContainer'),
       output = document.getElementById('output'),
       nextVideo,
       videoObjects =
       [
           document.createElement('video'),
           document.createElement('video')
       ],
       vidSources =
       [
       """ + text_vars + """ 
       ],
       nextActiveVideo = Math.floor((Math.random() * vidSources.length));

   videoObjects[0].inx = 0; //set index
   videoObjects[1].inx = 1;

   initVideoElement(videoObjects[0]);
   initVideoElement(videoObjects[1]);

   videoObjects[0].autoplay = true;
   videoObjects[0].src = vidSources[nextActiveVideo];
   videoObjects[0].autoplay = true;
   videoObjects[0].width = 640;
   videoObjects[0].height= 360;
   videoObjects[0].setAttribute("controls","controls")
   videoContainer.appendChild(videoObjects[0]);

   videoObjects[1].style.display = 'none';
   videoObjects[1].autoplay = true;
   videoObjects[1].width = 640;
   videoObjects[1].height= 360;
   videoContainer.appendChild(videoObjects[1]);

   function initVideoElement(video)
   {
       video.playsinline = true;
       video.muted = false;
       //video.preload = 'auto'; //but do not set autoplay, because it deletes preload
       video.autoplay = true;
       video.setAttribute("controls","controls")
       video.play()

       video.onplaying = function(e)
       {
           //output.innerHTML = 'Current video source index: ' + nextActiveVideo;
           nextActiveVideo = ++nextActiveVideo % vidSources.length;
           if(this.inx == 0)
               nextVideo = videoObjects[1];
           else
               nextVideo = videoObjects[0];
           nextVideo.src = vidSources[nextActiveVideo];
           nextVideo.pause();
       };

       video.onended = function(e)
       {
           this.style.display = 'none';
           nextVideo.style.display = 'block';
           nextVideo.play();
       };
   }
   </script>
   """

   return(js)
