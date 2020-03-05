$(function() {
   var $playpause, video;
   if($('#main_video_player').length!=0) {
      $playpause = $('button[name=playersPlay]');
      video = $('#main_video_player video')
      var controlFunction = function (e) {
         var playpause = this; 
     
         if (video.paused || video.ended) {
             playpause.title = "pause";
             playpause.innerHTML = "pause";
             video.play();
         } else {
             playpause.title = "play";
             playpause.innerHTML = "play";
             video.pause();
         }
     };
   }

}) 