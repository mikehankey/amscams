$(function() {
   $('#star_picker_background').click(function() {
      change_canvas_bg();
   });

   $('#radec_mode').click(function() {
 
      if(typeof json_reduced  == "undefined") {
         loading_done();
         bootbox.alert({
             message: "JSON file is missing. A JSON files with calibration parameters is required (-reduced.json).<br/>",
             className: 'rubberBand animated error',
             centerVertical: true 
         });
      } else {
         RADEC_MODE = !RADEC_MODE;
       
         if(RADEC_MODE) {
            // We hide the stars
            remove_stars_info_from_canvas();
   
            // We add the radec panel
            build_radecpanel();
            
   
         } else {
            // We put back the stars
            add_stars_info_on_canvas();
   
            // Remove the radec info from canvas
            remove_radec_info_from_canvas();
   
            // We empty rad_dec_object
            rad_dec_object = [];
   
            // We delete the panel
            $('#select_f_tools').remove();
         }
      }
   
      
   })
})
