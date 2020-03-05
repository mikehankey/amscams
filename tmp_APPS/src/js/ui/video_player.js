$(function() {
   var playpause, video;
   if($('#main_video_player').length!=0) {
      playpause = document.getElementsByClassName("playpause");
      video = document.getElementById("main_video_player");

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

      // For each play pause button
      for (var i = 0; i < playpause.length; i++) {
         playpause[i].addEventListener('click', controlFunction, false);
      }

      // Video methods
      var videoPlayFunction = function () {
         var playpause = this;
         playpause.title = "pause";
         playpause.innerHTML = "pause";
      };
      var videoPauseFunction = function () {
         var playpause = this;
         playpause.title = "play";
         playpause.innerHTML = "play";
      };

      // For each video adds the event listeners
      for (var i = 0; i < video.length; i++) {
         video[i].addEventListener('play', videoPlayFunction, false);
         video[i].addEventListener('pause', videoPauseFunction, false);
         video[i].controls = false;
      }
   }

}) 