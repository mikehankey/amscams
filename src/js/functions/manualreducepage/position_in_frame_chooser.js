
var frames_done=[];  // Just for the frames done
var frames_jobs=[];  // All the info for the frames done

// Fix the height of the chooser
function fix_pifc_ui() {
   var fh =$('#footer').outerHeight();

   if($(window).outerHeight()-fh-$('#main_container').outerHeight() < 20) {
      while($(window).outerHeight()-fh-$('#main_container').outerHeight() < 20) {
         $('#cropped_frame_selector').width($('#cropped_frame_selector').width()-1)
       }
   }
}


// Function Init position chooser tools
function init_pos_choos() {

   // Fix height
   fix_pifc_ui();

   // Add first frame to picker
   $('#cropped_frame_selector').find('img').attr('src',$($('#cropped_frame_select').find('img').get(0)).attr('src'))



}


 