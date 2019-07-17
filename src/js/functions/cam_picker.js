$(function() {

    $('.cam_picker').each(function() {
     
        if(typeof $(this).attr('data-url-param') != undefined) {
            $(this).change(function() {
                var $t = $(this);
                var cur_params = getQueryParameters();
                var param_to_update = $t.attr('data-url-param');
                cur_params[param_to_update] = $(this).val();
                setQueryParameters(cur_params); // Defined in date_picker.js
            });
        }
    }) 

})