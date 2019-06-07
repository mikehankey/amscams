function new_solve_field() {
    new_make_plate(); // Make Plate First
    check_solve_field_status(1);
}


function check_solve() {
   $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: {
            cmd: 'solve_field',
            hd_stack_file: hd_stack_file, // Defined on the page
        },
        success:function(data) {
           // console.log('CHECK SOLVE ', $.parseJSON(data));
            sleep(5000).then(() => {
                check_solve_field_status(0)
             });
        }
    });
}

function check_fit_status(data) {
    if(data['status'] == 'done') {
        bootbox.confirm("Do you want to run Fit Field again", function(result){ 
            if(result) {
                $.ajax({
                    url:  "/pycgi/webUI.py",
                    data: {
                        cmd: fit_field,
                        override:1,
                        hd_stack_file: hd_stack_file
                    },
                    success:function(data) {
                        var json_resp = $.parseJSON(data);
                        alert(json_resp['message']);
                    }
                })
            }
        });
    } else {
        /*
        NOTHING
        bootbox.alert({
            message: data['message'],
            className: 'rubberBand animated error',
            centerVertical: true
        });
        */
    }
}
     

function check_solve_field_status(step) {
    var cmd_data = {
		cmd: 'check_solve_status',
        hd_stack_file: hd_stack_file, // Defined on the page
    };

    loading({text: "Solving the Field<br/><small>This process can take up to 5 minutes</small>"});

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
            var json_resp = $.parseJSON(data);
            var status = json_resp['status'];

            if(status == 'new' && step==1) {
                
                // Check astrometry.net plate 
                check_solve();

            } else if(status == 'failed' && step== 1) {
                
                // Failure
                bootbox.confirm("The job already ran and failed. Click 'Ok' to try again.", function(result){ 
                    if(result) {
                        check_solve();
                    }
                });

            } else if(status == 'running' && step == 0) { 

                loading({text: "Plate solving<br/><small>Please wait...</small>"});

                sleep(5000).then(() => {
                    check_fit_status(json_resp)
                });

            } else  if (status == 'success') {

                sleep(1000).then(() => {
                    bootbox.alert({
                        message: "Astrometry.net successfull solved the plate (return solve_field???).",
                        className: 'rubberBand animated',
                        centerVertical: true
                    });
   
                   // Add the grid to the image
                   canvas.setBackgroundImage(json_resp['grid_file'], canvas.renderAll.bind(canvas));
                   // Add the grid to the page so the show/hide grid button can work
                   az_grid_file = json_resp['grid_file'];
                   $('#show_grid_holder').removeAttr('hidden');  // Show the button
                   loading_done();
                });

            } else if(status == 'failed' && then_run == 0) {
                
                bootbox.alert({
                    message: "Astrometry.net failed to solved the plate.",
                    className: 'rubberBand animated error',
                    centerVertical: true
                }); 
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