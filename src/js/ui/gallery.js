$(function() {
 

        // Show over
        $('.mtt')
        .mouseover(function() {
            var $l   = $(this);
            var $img = $(this).find('img'); 
            $img.attr('data-org',$img.attr('src'));
            $img.attr('src',$l.attr('data-obj')); 

        })
        .mouseout(function() {
            var $img = $(this).find('img');
            $img.attr('src', $img.attr('data-org')).removeAttr('data-org');
        });


   
})