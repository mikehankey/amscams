function active_tool_bar_menu(id) {
   
   // Reset the RA/DEC Mode 
   if(RADEC_MODE) {
      radec_action();
   }

   // Remove the Star Background Picker
   $("#bg_selector").remove();

   $('#canvas_toolbar .btn').removeClass('active');
   $('#canvas_toolbar .btn#'+ id).addClass('active');
}

$(function() {
   $('#star_picker_background').click(function() {
      active_tool_bar_menu('star_picker_background');
      change_canvas_bg();
   });

   $('#radec_mode').click(function() {
      active_tool_bar_menu('radec_mode');
      radec_action();
   });

   $('#star_mode').click(function() {
      active_tool_bar_menu('star_mode'); 
   });


      
})
