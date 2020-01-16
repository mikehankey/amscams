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
   $('#star_picker_background').click(function(e) {
      e.stopImmediatePropagation();
      active_tool_bar_menu('star_picker_background');
      change_canvas_bg();
      return false;
   });

   $('#radec_mode').click(function(e) {
      e.stopImmediatePropagation();
      active_tool_bar_menu('radec_mode');
      radec_action();
      return false;
   });

   $('#star_mode').click(function(e) {
      e.stopImmediatePropagation();
      active_tool_bar_menu('star_mode'); 
      return false;
   });


      
})
