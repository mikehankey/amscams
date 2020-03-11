$(function() {


  // Show video preview on mousover on Gallery Daily Report
  if($('a.T[data-src]').length>0) {
      $('a.T[data-src]').each(function() {
         var $t = $(this);
         var video_path = $t.attr('data-src');
         if(video_path !== 'X') {
            $t.hover(function() { $('#vvv').remove(); $('<video id="vvv" style="width:100%" autoplay loop><source src="'+video_path+'"></video>').prependTo($t); });
         } else {
            $('#vvv').remove(); 
            $t.css('cursor','not-allowed')
         }

           
      })
  }

})
 