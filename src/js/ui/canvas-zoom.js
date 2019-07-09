$(function() {

    $('#zoom_canvas').click(function() {
        if($('#c').hasClass('r-zoomed')) {
            $('#c').removeClass('r-zoomed');
        } else {
            $('#c').addClass('r-zoomed');
        }
    });
})