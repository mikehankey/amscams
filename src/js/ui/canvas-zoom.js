$(function() {

    // Full zoom on canvas
    $('#zoom_canvas').click(function() {
        if($('#c').hasClass('r-zoomed')) {
            $('#c').removeClass('r-zoomed');
            $(this).removeClass('zoom-btn-f').find('i').removeClass('icon-zoom-out').addClass('icon-zoom-in');
        } else {
            $('#c').addClass('r-zoomed');
            $(this).addClass('zoom-btn-f').find('i').removeClass('icon-zoom-in').addClass('icon-zoom-out');
        }
    });
})