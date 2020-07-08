$(function() {


  // Show video preview on mousover on Gallery Daily Report
  if($('a.T[data-src]').length>0) {


      $('a.T[data-src]').mouseover(function() {
         var $t = $(this);
         var video_path = $t.attr('data-src');

         if(typeof video_path !== 'undefined' && video_path!=="X") {
            if($t.find('video').length>0) {
               $t.find('video').show();
            } else {
               $('<video style="width:100%" autoplay loop><source src="'+video_path+'"></video>').prependTo($t);
            }
         }

      });

      $('a.T[data-src]').mouseout(function() {
         var $t = $(this);
         $t.find('video').hide();
      });
   
   }
 

})
 