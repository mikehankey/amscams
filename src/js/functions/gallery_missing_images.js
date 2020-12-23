$(function() {


    if($('.gal-resize').length!=0) {

        $('.preview img').each(function() {
            var $img = $(this);
            var url = $img.attr('src');
            $.get(url)
            .fail(function() { 
                //console.log('NOT FOUND ', url)
                $img.attr('src','/dist/img/proccessing.png').addClass('process');
            })

        });

    }

  

})
