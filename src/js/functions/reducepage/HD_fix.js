// Just to confirm
function HD_fix_confirm() {

   bootbox.confirm({
      message: "Use this function if the meteor doesnt appear in the HD OR in the SD video. <b>The defecting video will be permanently replaced by a resized version of the SD or HD video.</b>",
      className: 'rubberBand animated info',
      centerVertical: true,
      buttons: {
         cancel: {
             label: 'Cancel'
         },
         confirm: {
             label: 'Continue'
         }
     },
     callback: function (result) {
        if(result==true) {
            show_stacks_to_fix();
        }
      }
   });
}


function show_stacks_to_fix() {
   // Build the modal
   $('#fix_video_modal').remove();
   $('<div id="fix_video_modal" class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">\
   <div class="modal-dialog modal-xl" role="document">\
     <div class="modal-content">\
      <div class="modal-header">\
        <h5 class="modal-title">Fix Video</h5>\
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
          <span aria-hidden="true">&times;</span>\
        </button>\
      </div>\
      <div class="modal-body">\
       <div class="row">\
         <div class="col-6">\
            <p>Below is the SD stack. Click the image if you want to<br><b>replace the HD video by the SD video</b>.</p>\
            <img src="'+sd_stack+'" class="img-fluid selectab" onclick="HD_SD_fix(\'SD\')"/>\
         </div>\
         <div class="col-6">\
            <p>Below is the HD stack. Click the image if you want to<br><b>replace the SD video by the HD video</b>.</p>\
           <img src="'+hd_stack+'" class="img-fluid selectab" onclick="HD_SD_fix(\'HD\')"/>\
         </div>\
        </div>\
     </div>\
   </div>\
 </div>').appendTo('body');
 $('#fix_video_modal').modal('show');
}


function HD_SD_fix(which) {

   if(which == 'SD') {
      var cmd_data = { 
         json_file: json_file,          // Defined on the page 
         cmd: 'replace_HD'
      };
      loading({text:'Replacing HD Data', overlay:true}); 
   } else {
      var cmd_data = { 
         json_file: json_file,          // Defined on the page 
         cmd: 'replace_SD'
       };
       loading({text:'Replacing SD Data', overlay:true}); 
   }
  

   
    
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
        
            var json_resp = $.parseJSON(data); 

            if(json_resp['status']!==0) {
               v = window.location;
               window.location = v.origin + v.pathname + "?cmd=reduce2&video_file=" + json_file + "&clear_cache=1&c" + Math.floor(Math.random(100000)*100000000)
               loading({text:'Recreating media and reloading page...', overlay:true});
            
            } else {
               loading_done();
               
               bootbox.alert({
                  message: json_resp['msg'],
                  className: 'rubberBand animated error',
                  centerVertical: true 
              });
            }

           
        }, error: function(data) {
            
            loading_done();
            bootbox.alert({
                message: "Something went wrong with the HD video deletion. Please, try again later",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
}


$(function() {
   $('#hd_fix').click(function() {
      HD_fix_confirm();
   })
})
