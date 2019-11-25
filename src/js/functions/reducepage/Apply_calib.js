$(function() {
   $('#reapply_calib').click(function() {
      var cmd_data = {
         json_file: json_file,          // Defined on the page 
         cmd: 'apply_calib'
      }

      loading({text:'Re-Applying calibration...', overlay:true}); 
      
      $.ajax({ 
         url:  "/pycgi/webUI.py",
         data: cmd_data,
         success: function(data) {
            
               window.location.reload()
   
         }, error: function(data) {
               
               loading_done();
               bootbox.alert({
                  message: "Something went wrong with the reduction data. Please, try again later",
                  className: 'rubberBand animated error',
                  centerVertical: true 
               });
         }
      });
   })
})
