// Manual Sync step 2
function manual_synchronization() {
   $('#sd_frame_selector a').click(function() {
      var $t = $(this), $img = $t.find('img');
      $('#sd_frame_selector a').removeClass('cur');
      $(this).addClass('cur');
 

      // Add image as preview bg
      $('#frame_selector_preview').css('background','url('+$img.attr('src')+')');

   })
}


 
 



$(function() {

   // Go to manual sync step 1
   $('#manual_synchronization').click(function(){ 
      window.location = './webUI.py?cmd=manual_sync&json=' + json_file +'&video=' + main_vid + '&stack=' + my_image + '&type=HD'
   })

})
