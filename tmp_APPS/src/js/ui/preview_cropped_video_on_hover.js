$(function() {

  if($('a.T[data-src]').length>0) {
      $('a.T[data-src]').each(function() {
         var $t = $(this);
         var video_path = $t.attr('data-src');
         $t.hover(function()  { $('<video id="vvv" style="width:100%" autoplay loop><source src="'+video_path+'"></video>').appendTo($t); });
         $t.blur(function()  { $('#vvv').remove()});
      })
  }

})
 