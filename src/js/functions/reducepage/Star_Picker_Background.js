// Change the background of the canvas by a single frame (instead of stack)
function change_canvas_bg() {

   loading({'text':'Creating background picker'});

   $.ajax({ 
      url:  "/pycgi/webUI.py",
      data: {
          cmd: 'get_HD_frames',
          json_file: json_file, // Defined in page 
      }, 
      success: function(data) {
         loading_done();
         data = JSON.parse(data); 
      }
   })

}


$(function() {
   $('#star_picker_background').click(function() {

   });
})
