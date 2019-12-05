// Just to confirm
function HD_fix_confirm() {

   bootbox.confirm({
      message: "Use this function if the meteor doesnt appear in the HD video. <b>The HD video will be permanently replaced by a resized version of the SD video.</b>",
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
           HD_fix();
        }
      }
   });
}


function HD_fix() {
   var cmd_data = { 
      json_file: json_file,          // Defined on the page 
      cmd: 'replace_HD'
    }

    loading({text:'Replacing HD Data', overlay:true}); 
    
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
        
            var json_resp = $.parseJSON(data); 

            if(json_resp['status']!==0) {
               v = window.location;
               window.location = v.origin + v.pathname + "?cmd=reduce2&video_file=" + json_file + "&clear_cache=1&c" + Math.floor(Math.random(100000)*100000000)
            }

            // No loading done
            //loading_done();
            loading({text:'Recreating media and reloading page...', overlay:true});
 
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
