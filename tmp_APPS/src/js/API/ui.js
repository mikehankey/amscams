function loading_button($btn) {
   $btn.attr('data-init',$btn.text()).css('width',$btn.width()).css('height',$btn.height())
   $btn.html('<img src="/APPS/dist/img/loader.svg" class="img-fluid"/>');
}

function load_done_button($btn) {
   $btn.text($btn.attr('data-init')); 
}