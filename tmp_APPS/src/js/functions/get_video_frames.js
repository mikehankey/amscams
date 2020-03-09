// Get all frames of a video as base64
async function extractFramesFromVideo(videoUrl, fps=25) {
   return new Promise(async (resolve) => {
 
     // fully download it first (no buffering):
     let videoBlob = await fetch(videoUrl).then(r => r.blob());
     let videoObjectUrl = URL.createObjectURL(videoBlob);
     let videoDD = document.createElement("videoXEDZ");
 
     let seekResolve;
     videoDD.addEventListener('seeked', async function() {
        console.log("VIDEO SEEKED");
       if(seekResolve) seekResolve();
     });
 
     videoDD.addEventListener('loadeddata', async function() {
       let canvas64 = document.createElement('canvasXEDZ');
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
     videoDD.src = videoObjectUrl; 
 
   });
 }

 let frames


 async function asyncCall() { 
   frames = await extractFramesFromVideo(cropped_video,1); 

   $.each(frames,function(i,v){ 
      // Add base64 thumbs to the table
      console.log(i);
      console.log(v);
      $('#thb_'+i + ' img').attr('src',v); 
   });

 
 }

 $(function() {
   console.log("OK");
   if(typeof cropped_video !== 'undefined') {
      asyncCall()
   }
 })