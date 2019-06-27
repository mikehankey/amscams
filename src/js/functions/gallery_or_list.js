function gallery_or_list() {
    $('#show_gal').click(function() {
        var $t = $(this);
        $('.gallery').toggleClass('list');
        if($('.gallery').hasClass('list')) {
            $t.find('i').removeClass().addClass('icon-gallery');
        } else {
            $t.find('i').removeClass().addClass('icon-list');
        }
    })
}


$(function() {
    gallery_or_list();
})