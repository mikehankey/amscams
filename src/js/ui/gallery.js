$(function() {

        // Show over
        $('.mtt')
        .mouseover(function() {
            var $img = $(this).find('img');
            $img.attr('data-org',$img.attr('src')).attr('src',$(this).attr('data-obj'));
        })
        .mouseout(function() {
            var $img = $(this).find('img');
            $img.attr('src', $img.attr('data-org')).removeAttr('data-org');
        });

})