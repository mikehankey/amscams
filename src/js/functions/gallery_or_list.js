function gallery_or_list() {
    $('#show_gal').click(function() {
        var $t = $(this);

         loading({'container':'moncul'});

         $('.gallery').toggleClass('list');
         $('body').toggleClass('list');
         if($('.gallery').hasClass('list')) {
            $t.find('i').removeClass().addClass('icon-gallery');
            // Add cookie for python
            Cookies.set('archive_view', "list", { expires: 99999, path: '/' });
         } else {
            $t.find('i').removeClass().addClass('icon-list');
            // Add cookie for python
            Cookies.set('archive_view', "gal", { expires: 99999, path: '/' });
         }

         loading_done();
    })
}


$(function() {
   gallery_or_list();
});