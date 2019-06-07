function new_make_plate() {
	var cmd_data = {
		cmd: 'make_plate_from_points',
        hd_stack_file: hd_stack_file, // Defined on the page
        points: ''
	}

    loading({text: "Making Plate for Astrometry.net ",overlay:true});
    
    // Get all selected stars (all circles on the canvas)
    var canvas_stars = canvas.getObjects('circle');
    $.each(canvas_stars, function(i,v) {
        if (v.get('type') == "circle" && v.get('radius') == 5) {
            cmd_data.points = cmd_data.points + v.left.toString() + "," + v.top.toString() + "|";
         }
    }); 
  
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
            var json_resp = $.parseJSON(data);

            // Remove stars from canvas
            for (let i in canvas_stars) {
                canvas.remove(canvas_stars[i]);
             }
            
            // Add plate to the canvas
            var new_img     = json_resp['half_stack_file_an'] + "?r=" + Math.random().toString();
            new_img.height  = 960;
            new_img.width   = 540;

            canvas.setBackgroundImage(new_img, canvas.renderAll.bind(canvas));

            var stars = json_resp['stars'];

            // Draw stars return by make_plate
            for (let s in stars) {

                cx = stars[s][0] - 11
                cy = stars[s][1] - 11
  
                var circle = new fabric.Circle({
                   radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                   selectable: false
                });
                canvas.add(circle);
  
            }  

            loading_done();

            bootbox.alert({
                message: "The Plate is done. We will now solving the field.",
                className: 'rubberBand animated',
                centerVertical: true, 
                callback: function () {
                    // Call solve_field on callback (STEP 2)
                    new_solve_field();
                }
            });
        }, 
        error:function() {
            bootbox.alert({
                message: "The process returned an error",
                className: 'rubberBand animated error',
                centerVertical: true
            });
            loading_done();
        }
    });
}
  


$(function() {
    $('#solve_field').click(function() {

        // First step:
        new_make_plate();

    })
})