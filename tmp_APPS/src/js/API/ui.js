function loading_button($btn) {
   var h=$btn.outerHeight(),w=$btn.width(),ih=$btn.innerHeight();
   $btn.attr('data-init',$btn.text()).attr('style','height:'+h+'px!important;width:'+w+'px!important')
   $btn.html('<img src="/APPS/dist/img/loader.svg" class="img-fluid" style="height:calc('+h+'px - 2*.25rem)"/>');
}

function load_done_button($btn) {
   $btn.text($btn.attr('data-init')); 
}