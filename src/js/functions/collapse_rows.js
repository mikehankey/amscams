$(function() {
    $('.toggler').click(function() { 
        var id = $(this).attr('data-tog');
        var $container = $(id);
        var $gal = $container.find('.gallery');

        if($container.hasClass('show')) {
            // Remove Gallery
            $gal.html('');
        } else {

            // Build Gallery
            $.each(all_cal_details[id.substr(1)], function(i,v){

                $('<div class="preview p-2"><a href="'+v.lk+'" class="mttt"><img src="'+v.src+'" class="ns" width="200" height="112"/> \\
                </a><span class="det" '+v.col+'><b>' + v.st + "</b> stars - <b>" + v.trp + "</b>Rpx - <b>" + .trd + "</b>Rd</span></div>").appendTo($gal);


            });
        }

        $container.toggleClass('show');
    });
    
})