 function make_it_blink($el) {
     $el.addClass('blinked');
     setTimeout(function() {
         $el.removeClass('blinked');
     },500);
 }