
function ajax_api_crop(crop_box) {
    x = crop_box[0]
    y = crop_box[1]
    w = crop_box[2]
    h = crop_box[3]
    var cmd_data = {
        video_file:       sd_video_file,          // Defined on the page
        x: x,
        y: y,
        w: w,
        h: h
    }
    loading({text:'Updating  reduction data...', overlay:true});

    $.ajax({
        url:  "/API/crop_video",
        data: cmd_data,
        success: function(data) {

            var json_resp = data;

            if(json_resp['status']!==0) {

                // Remove All objects from Canvas with type =   type: 'reduc_rect'
                //remove_reduction_objects_from_canvas();

                // Update Reduction
                //update_reduction_on_canvas_and_table(json_resp);

                // Update Add frames
                //setup_add_frames();

            }

            //reduction_table_actions();

            //if(callback!='') {
            //  callback();
            //}

            loading_done();
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
}

function refit_meteor() {
    var cmd_data = {
        video_file:       sd_video_file,          // Defined on the page
    }
    alert("Please wait a moment for the page to reload.")
    $.ajax({
        url:  "/API/refit_meteor",
        data: cmd_data,
        success: function(data) {
            var json_resp = data;
            //if(json_resp['status']!==0) {

                // Remove All objects from Canvas with type =   type: 'reduc_rect'
                //remove_reduction_objects_from_canvas();
                // Update Reduction
                //update_reduction_on_canvas_and_table(json_resp);
                // Update Add frames
                //setup_add_frames();
            //}
            //reduction_table_actions();
            //if(callback!='') {
            //  callback();
            //}
            //loading_done();
            window.location.reload()
        }, error: function(data) {

            //loading_done();
            //bootbox.alert({
            //    message: "Something went wrong with the reduction data. Please, try again later",
            //    className: 'rubberBand animated error',
            //    centerVertical: true
            //});
        }
    });


}

function man_reduce() {


   var modal = document.getElementById("myModal");


   // Get the <span> element that closes the modal
   var span = document.getElementsByClassName("close")[0];




   // sd_video_file
   var objects = canvas.getObjects() 
   var cc = 0
   var cxpoints = []
   var cypoints = []
   $.each(objects,function(i,v){
      console.log(v.type)
      if(v.type=='circle') {
        cc = cc + 1
        x = parseInt(v.left)
	y = parseInt(v.top)
	console.log(typeof(x))
        cxpoints.push(x)
        cypoints.push(y)
      }

      else {
         canvas.remove(objects[i]);
      }

    });

   
   if (cc != 2) {
      $.each(objects,function(i,v){
         canvas.remove(objects[i]);
      })
      // add text instructions since there are not 2 points
      var res_desc = "Step 1 : Click near the start and end points of the meteor and then press manual reduce." 
      canvas.add(new fabric.Text(res_desc , {
                fontFamily: 'Arial',
                fontSize: 12,
                left: 5,
                top: 518,
                fill: 'rgba(255,255,255,.75)',
                selectable: false
      }));
      return
    }
    var min_x = Math.min.apply(Math, cxpoints)
    var min_y = Math.min.apply(Math, cypoints)
    var max_x = Math.max.apply(Math, cxpoints)
    var max_y = Math.max.apply(Math, cypoints)
    var cw = max_x - min_x
    var ch= max_y - min_y
    crop_box = []
    crop_box.push(min_x)
    crop_box.push(min_y)
    crop_box.push(cw)
    crop_box.push(ch)
    // Add crop box to canvas
    canvas.add(
    new fabric.Rect({
       fill: 'rgba(0,0,0,0)',
       strokeWidth: 1,
       stroke: 'rgba(230,230,230,.2)',
       left: crop_box[0],
       top: crop_box[1],
       width: crop_box[2],
       height: crop_box[3],
       selectable: false
       })
     );

     //ajax_api_crop(crop_box ) 
     x = crop_box[0]
     y = crop_box[1]
     w = crop_box[2]
     h = crop_box[3]
     //alert("HELLO:")
     man_url = "/meteor_man_reduce/?file=" + sd_video_file + "&x=" + x + "&y=" + y + "&w=" + w + "&h=" + h
     document.getElementById('modal_url').src = man_url;
     modal.style.display = "block";
     //window.location.replace(man_url)

}
