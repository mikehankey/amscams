// Get all frames of a video as base64
async function extractFramesFromVideo(videoUrl, fps=25) {
   return new Promise(async (resolve) => {
 
     // fully download it first (no buffering):
     let videoBlob = await fetch(videoUrl).then(r => r.blob());
     let videoObjectUrl = URL.createObjectURL(videoBlob);
     let videoDD = document.createElement("video");
 
     let seekResolve;
     videoDD.addEventListener('seeked', async function() {
       if(seekResolve) seekResolve();
     });
 
     videoDD.addEventListener('loadeddata', async function() {
       let canvas64 = document.createElement('canvas');
       let contextWW = canvas64.getContext('2d');
       let [w, h] = [videoDD.videoWidth, videoDD.videoHeight]
       canvas64.width =  w;
       canvas64.height = h;
 
       let frames = [];
       let interval = 1 / fps;
       let currentTime = 0;
       let duration = videoDD.duration;
 
       while(currentTime < duration) {
         videoDD.currentTime = currentTime;
         await new Promise(r => seekResolve=r);
 
         contextWW.drawImage(videoDD, 0, 0, w, h);
         let base64ImageData = canvas64.toDataURL();
         frames.push(base64ImageData);
 
         currentTime += interval;
       }
       resolve(frames);
});
 
     // set video src *after* listening to events in case it loads so fast
     // that the events occur before we were listening.
     video.src = videoObjectUrl; 
 
   });
 }

 let frames


 async function asyncCall() { 
   frames = await extractFramesFromVideo($('#main_video_player source').attr('src')); 

   $.each(frames,function(i,v){
      console.log(v);
      $('<img src="'+v+'"/>').prependTo($('#main_container'));
   });

 
 }

 $(function() {
    if($('#main_video_player').lenght!==0) {
       asyncCall()
    }
 })