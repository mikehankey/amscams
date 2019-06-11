function upscale_HD(img_url) {
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

    ajax_url = "/pycgi/webUI.py?cmd=upscale_2HD&hd_stack_file=" + hd_stack_file + "&points=" + point_str
    console.log(ajax_url)
    $.get(ajax_url, function(data) {
       $(".result").html(data);
       var json_resp = $.parseJSON(data);
       var new_img = json_resp['hd_stack_file'] 
       var new_url = "webUI.py?cmd=free_cal&input_file=" + new_img
       alert("Upscale Complete!")
       window.location.replace(new_url);

    });
 }