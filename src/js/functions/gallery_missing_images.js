$(function() {


    if($('.gal-resize').length!=0) {

        $('.preview img').each(function() {
            var url = $(this).attr('src');
            $.get(url)
            .fail(function() { 
                console.log('NOT FOUND ', url)
                $(this).attr('src','./dist/img/proccessing.png')
            })

        });

    }

  

})