function gallery_or_list() {
    $('#show_gal').click(function() {
        var $t = $(this);
        $('.gallery').toggleClass('list');
        if($('.gallery').hasClass('list')) {
            $t.find('i').removeClass().addClass('icon-gallery');
            Cookies.set('archive_view', "list", { expires: 99999, path: '/' });
        } else {
            $t.find('i').removeClass().addClass('icon-list');
            Cookies.set('archive_view', "gal", { expires: 99999, path: '/' });
        }
    })
}


$(function() {
   

   gallery_or_list();
   
   // List ?
   //if(Cookies.get('archive_view')=='list') {
   //   $('#show_gal').click();
   //}

});


