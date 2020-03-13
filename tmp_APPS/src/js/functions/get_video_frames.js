async function extractFramesFromVideo(videoUrl,firstframe,fps=25) {
   return new Promise(async (resolve) => {
 
     // fully download it first (no buffering):
     let videoBlob = await fetch(videoUrl).then(r => r.blob());
     let videoObjectUrl = URL.createObjectURL(videoBlob);
     let video = document.createElement("video");
 
     let seekResolve;

     video.addEventListener('seeked', async function() {
       if(seekResolve) seekResolve();
     });
 
     video.addEventListener('loadeddata', async function() {
       let canvas = document.createElement('canvas');
       let context = canvas.getContext('2d');
       let [w, h] = [video.videoWidth, video.videoHeight]
       canvas.width =  w;
       canvas.height = h;
 
       let frames = [];
       let interval = 1 / fps;
       let currentTime = 0;
       let duration = video.duration;
 
       while(currentTime < duration) {
         video.currentTime = currentTime;
         await new Promise(r => seekResolve=r);
         
         if(frames.length>firstframe) {
            context.drawImage(video, 0, 0, w, h);
            let base64ImageData = canvas.toDataURL();
            frames.push(base64ImageData);
         }
         
 
         currentTime += interval;
       }
       resolve(frames);
     });
 
     // set video src *after* listening to events in case it loads so fast
     // that the events occur before we were listening.
     video.src = videoObjectUrl; 
 
   });
 }
 
 
 let croppedFrames
 
 async function asyncCall(first_frame) {  
   croppedFrames = await extractFramesFromVideo(cropped_video,first_frame); 

   $.each(croppedFrames,function(i,v){  
      // Add base64 thumbs to the table 
      $('#thb_'+i).find('img').attr('src',v).css('border-color', $('#thb_'+i).attr('data-src')); 
   });

   // We enable the frame by frame animation when it's loaded
   $('#play_anim_tv').removeClass('disabled');
 }

 $(function() {  

   if(typeof cropped_video !== 'undefined') {

      // What's the first frame we want to get?
      asyncCall(first_frame)
   }
 })