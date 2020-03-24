async function extractFramesFromVideo(videoUrl,firstframe, how_many_frames, fps=25) {
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
       let frame_counter = 0;
       let frames = [];
       let interval = 1 / fps;
       let currentTime = 0;
       let duration = video.duration;
 
       while(currentTime < duration) {
         video.currentTime = currentTime;
         await new Promise(r => seekResolve=r);
          
         if(frame_counter>=firstframe && frames.length<= how_many_frames) {
            //console.log("FRAME ADDED - FRAME COUNTER :" + frame_counter);
            context.drawImage(video, 0, 0, w, h);
            let base64ImageData = canvas.toDataURL();
            frames.push(base64ImageData);
         
            if(how_many_frames<=frames.length) {
               //console.log("BREAK")
               break;
            }
         
         }  
         
         frame_counter++;
 
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
 
 async function asyncCall(first_frame, how_many_frames) {  
   croppedFrames = await extractFramesFromVideo(cropped_video,first_frame, how_many_frames); 


   var i, frame_c = 0;
   for (i = first_frame-1; i <=  (first_frame+how_many_frames+1); i++) {
       // Add base64 thumbs to the table  
       $('#thb_'+i).find('img').attr('src',croppedFrames[frame_c]).css('border-color', $('#thb_'+i).attr('data-src')).css('max-width','180px'); 
       frame_c++;
   }

   // We enable the frame by frame animation when it's loaded
   $('#play_anim_tv').removeClass('disabled');

   load_done_button($("#play_anim_tv"));
   load_done_button($(".fr_only"));


   // Setup Meteor Picker (Manual Reduce1) 
   // ONLY WHEN FRAMES ARE LOADED (!) 
   setup_manual_reduc1();
 }

 $(function() {  

   if(typeof cropped_video !== 'undefined') {
  
      // Frame by frame animation holding
      loading_button($("#play_anim_tv"));
      loading_button($(".fr_only"));
  
      // What's the first frame we want to get?
      asyncCall(first_frame, how_many_frames)
   }
 })