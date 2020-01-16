function active_tool_bar_menu(id) {
   // Remove RA/Dec Mode
      // We put back the stars
      add_stars_info_on_canvas();

      // Remove the radec info from canvas
      remove_radec_info_from_canvas();

      // We empty rad_dec_object
      rad_dec_object = [];

      // We delete the panel
      $('#select_f_tools').remove();

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
