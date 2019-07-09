$(function() {

    // Full zoom on canvas
    $('#zoom_canvas').click(function() {
        if($('#c').hasClass('r-zoomed')) {
            $('#zc').remove();
            $('#c').removeClass('r-zoomed');
            $(this).removeClass('zoom-btn-f').find('i').removeClass('icon-zoom-out').addClass('icon-zoom-in');
        } else {
            $('<div id="zc" class="modal-backdrop fade show"></div>').appendTo($('body')).click(function(){
                $('#zoom_canvas').click();
            });
            $('#c').addClass('r-zoomed');
            $(this).addClass('zoom-btn-f').find('i').removeClass('icon-zoom-in').addClass('icon-zoom-out');
        }
    });
})