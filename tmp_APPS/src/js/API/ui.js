function loading_button($btn) {
   $btn.attr('data-init',$btn.text());
   $btn.html('<img src="/dist/img/loader.svg"/>');
}

function load_done_button($btn) {
   $btn.text($btn.attr('data-init')); 
}