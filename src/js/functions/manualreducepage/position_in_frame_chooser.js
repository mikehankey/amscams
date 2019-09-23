function fix_pifc_ui() {
   var fh =$('#footer').outerHeight();

   if($(window).outerHeight()-fh-$('#main_container').outerHeight() < 20) {
      while($(window).outerHeight()-fh-$('#main_container').outerHeight() < 20) {
         $('#cropped_frame_selector').width($('#cropped_frame_selector').width()-1)
       }
   }

