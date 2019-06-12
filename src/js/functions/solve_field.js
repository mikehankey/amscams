function new_solve_field() {
    new_check_solve_status(1);
}

function new_check_solve_status(step) {
    
    var cmd_data = {
		cmd: 'check_solve_status',
        hd_stack_file: hd_stack_file  // Defined on the page
    };
    
    loading({'text':'Solving Field...',overlay:'true'});
  
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
            var json_resp = $.parseJSON(data);
            var status = json_resp['status'];

            if(status=='new' && step==1) {
                loading_done();
                bootbox.alert({
                    message: "We will now run Astrometry.net plate solve on selected stars.",
                    className: 'rubberBand animated',
                    centerVertical: true, 
                    callback: function () {
                        send_ajax_solve();
                    }
                });
            } else if(status ==='running' && step==0) {
                loading_done();
                loading({'text':'Still Solving Field...',overlay:'true'});
                setTimeout(function() {
                    check_fit_status(json_resp);
                }, 5000);
            } else if(status=='success') {
                // Update grid on canvas
                grid_img = json_resp['grid_file'];
                canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
                loading_done();
            } else if(status=='failed' && step ==0) {
                
            }
        }
    });
  
       if (json_resp['status'] == 'success' && then_run == 1) {
          grid_img = json_resp['grid_file']
          alert("Astrometry.net successfully solved the plate.")
          document.getElementById('star_panel').innerHTML = "Astrometry.net successfully solved the plate."
          canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
          //alert(json_resp['debug'])
       }
       if (json_resp['status'] == 'failed' && then_run == 0) {
          alert("Astrometry.net failed to solved the plate.")
          document.getElementById('star_panel').innerHTML = "Astrometry.net failed to solved the plate."
          //alert(json_resp['solved_file'])
          alert("failed")
       }
    });
}