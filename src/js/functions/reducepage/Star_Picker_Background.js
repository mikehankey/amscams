// Create BG Picker
function create_bg_picker(data) {

   var max_height = $(window).height() - 200;

   var img_list = '<div class="box" style="position:absolute; width: 400px; top:0;  z-index:99999"> <h2 class="mb-0"><a data-toggle="collapse" href="#bg_box" role="button" class="d-block dropdown-toggle dt-title" aria-expanded="true">Background</a></h2><div id="bg_box" class="pt-2 collapse show"><div style"height:'+max_height+'px;overflow:auto" class="gallery gal-resize row text-center text-lg-left overflow-x:auto; ">';

   
   // Create list of image picker
   $.each(data,function(i,v) {
      img_list += '<div class="preview col-md-6 select-to mb-3"><a class="mtt has_soh"  title="Select Background"><img alt="" src="'+v+'"></a></div>';
   });

   img_list += "</div></div></div>";

   $(img_list).prependTo($('.flex-fixed-r-canvas.h-100')); 
    
   
}


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
         create_bg_picker(data.res);
      }
   })

}


$(function() {
   $('#star_picker_background').click(function() {
      change_canvas_bg();
   });
})
