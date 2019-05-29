var loading_interval;

function loading(overlay, text) {
    var real_text = text;

    overlay = overlay || 0;
    text = text || 'Loading...';

    if(!text.endsWith("...", text.lenght)) {
        text = text + "...";
    } 
    var $s = $('.navbar-brand .tx span.s');
    var $m = $('.navbar-brand .tx span.m');
   
    $('.navbar-brand').find('.tx').find('span').each(function() {
        $(this).attr('data-src',$(this).text());
    });

    $m.text(text);
    $s.text('...');

    // Overlay Option
    if(overlay) {
        $('body').css('overflow','hidden');
        $('<div id="overlay" class="animated"><div class="row h-100 text-center"><div class="col-sm-12 my-auto"><div class="card card-block" style="background:transparent"><iframe style="zoom: 1.8;border:0;margin: 0 auto;" src="./dist/img/anim_logo.svg" width="140" height="90"></iframe><h3>'+text+'</h3></div></div></div></div>').appendTo($('body'));
        $o = $('#overlay h2');
    }
 
    $("#logo_holder").contents().find("#logo").addClass("animated");

    loading_interval = setInterval(function() {
        if($m.text() == real_text + '...') $m.text(real_text);
        if($s.text() == '...')        $s.text('');
 
        $m.text($m.text()+'.');
        $s.text($s.text()+'.');
    },250);
}

function loading_done() {
    clearInterval(loading_interval);

    // Reset title
    $('.navbar-brand').find('.tx').find('span').each(function() {
        $(this).html($(this).attr('data-src'));
    });
    $("#logo_holder").contents().find("#logo").removeClass("animated");

    // Remove Overlay 
    $('#overlay').fadeOut(150, function() {$('#overlay').remove();})

    $('body').css('overflow','auto');

} 
 