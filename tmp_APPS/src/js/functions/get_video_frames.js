// Get all frames of a video as base64
async function extractFramesFromVideo(videoUrl, fps=25) {
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
 
         context.drawImage(video, 0, 0, w, h);
         let base64ImageData = canvas.toDataURL();
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
      $('<img src='+v+'/>').preprendTo(($('#main_container'));
   });


   console.log(frames);
 }

 $(function() {
    if($('#main_video_player').lenght!==0) {
       asyncCall()
    }
 })