
$(function() {
    // Update URL on calibration selection
    $('#cal_param_selected').change(function() { 
        window.location.href="webUI.py?cmd=calibration&cams_id=" + $(this).val();
    });
});