// Delete Calibration Parameters
function delete_calibration() {
    bootbox.confirm("Are you sure you want to permanently delete the current calibration parameters?", function(result){ 
        if(result) {
            loading({text:"Deleting Calibration Parameters", overlay:true});
            $.ajax({ 
                url:  "/pycgi/webUI.py",
                data: {
                    hd_stack_file: hd_stack_file, // Defined on the page
                    cmd: 'delete_cal'
                },
                success: function(data) {
                    loading_done();

                    // Avoid "unsaved" message from canvas_interactions 
                    // if the user selected some stars
                    $(window).unbind('beforeunload');

                    // I guess it always goes smoothly??
                    bootbox.alert({
                        message: "The page will now reload",
                        className: 'rubberBand animated',
                        centerVertical: true,
                        callback: function () {
                            location.reload();
                        }
                    });
                }
            });
        }
    });
}



$(function() {
    $('#delete_calibration').click(function() {
        delete_calibration();
    });
})