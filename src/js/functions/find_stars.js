
// FROM hd_stack_file 
function find_stars() {
	var cmd_data = {
		cmd: 'find_stars_ajax',
		stack_file: hd_stack_file // Defined on the page
	}

	loading({text: "Automatically Finding Stars",overlay:true});

	$.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
        	try {
		  		var json_resp = $.parseJSON(data);
         		var auto_stars = json_resp['stars'];

         		for (let s in auto_stars) {
		            x = auto_stars[s][0] / 2;
		            y = auto_stars[s][1] / 2;
		            var circle = new fabric.Circle({
		               radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: x-5, top: y-5,
		               selectable: false
		            });
		            canvas.add(circle);
		         }

		        if(auto_stars.length>1) {
		        	bootbox.alert({
		                message: auto_stars.length + " stars have been found.<br/>You can now select more (bright) stars before solving the Field.",
		                className: 'rubberBand animated',
		                centerVertical: true
		            });
		        } else {
		        	bootbox.alert({
		                message: "We couldn't find any stars. Please, select (bright) stars before solving the Field.",
		                className: 'rubberBand animated',
		                centerVertical: true
		            });		        	
		        }
		  
		        $('#solve_field_info').removeClass('hidden');
		        loading_done();
			}
			catch(err) {
		  		bootbox.alert({
	                message: "The process returned an error - " + err,
	                className: 'rubberBand animated error',
	                centerVertical: true
            	});

            	 loading_done();
			}

            
           
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
	$('.auto_detect_stars').click(function() {
		find_stars();
	})
})