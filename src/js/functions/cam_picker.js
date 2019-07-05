$(function() {

    $('.cam_picker').each(function() {
        if($(this).hasAttr('data-url-param')) {
            $(this).change(function() {
                var param_to_update = $t.attr('data-url-param');
                setQueryParameters($(this).val());
            });
        }
    }) 

})