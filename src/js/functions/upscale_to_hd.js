
function upscale_to_HD() {
    loading({text:"Upscaling to HD...", overlay:true});

    var point_str = ""
    for (i in user_stars) {
       point_str = point_str + user_stars[i].toString()  + "|"
    }

    var point_str = ""
    var objects = canvas.getObjects('circle')
    for (let i in objects) {
       x = objects[i].left
       y = objects[i].top
       if (objects[i].get('type') == "circle") {
       point_str = point_str + x.toString() + "," + y.toString() + "|"
       }
    } 

    $.ajax({ 
          url:  "webUI.py?cmd=upscale_2HD",
          data: {
            hd_stack_file: hd_stack_file,
            points:point_str
          },
          success: function(data) {
                loading({text:"Upscaling COMPLETE", overlay:true});
                setTimeout(function() {
                    var json_resp = $.parseJSON(data);
                    var new_img = json_resp['hd_stack_file'] 
                    var new_url = "webUI.py?cmd=free_cal&input_file=" + new_img 
                    window.location.replace(new_url);
                    loading_done();
                    },1000)
          }, 
          error: function() {
                alert('Impossible to upscale. Please try again later')
                loading_done();
          }
    });
}

 