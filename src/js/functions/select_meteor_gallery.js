$(function() {

    var $sel = $('input[name=meteor_select]');
    if($sel.length!==0) {

        $sel.on('change',function() {
            var id = $(this).attr('id');
            loading({"text":"Selecting meteors..."});
            switch (id) {
                case "reduced":
                    // Reduced Only
                    $('.preview.norm').fadeOut();
                    $('.preview.reduced').fadeIn();
                    break;
                case "non_reduced":
                   // Reduced Only
                   $('.preview.norm').fadeIn();
                   $('.preview.reduced').fadeOut();
                   break;
                default:
                    $('.preview.norm').fadeIn();
            }
            loading_done();
         });


    }
})