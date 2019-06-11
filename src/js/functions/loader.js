var loading_interval;

function loading(options) {

    loading_done(); // Avoid multiple
    $('#top_overlay').remove();

    if(typeof options !== 'undefined') {
        options.text    = typeof options.text == 'undefined' ? 'Loading': options.text;
        options.overlay = typeof options.text == 'undefined' ? true : options.overlay; 
    } else {
        options = {
            text: 'Loading',
            overlay: true,
            element: 'body'        
        };
    }
 
    // Overlay Option
    if(options.overlay === true) {
        $('body').css('overflow','hidden');
        $('<div id="overlay" class="animated"><div class="row h-100 text-center"><div class="col-sm-12 my-auto"><div class="card card-block" style="background:transparent"><iframe style="zoom: 1.8;border:0;margin: 0 auto;" src="./dist/img/anim_logo.svg" width="140" height="90"></iframe><h3>'+options.text+'</h3></div></div></div></div>').appendTo($('body'));
    } else {
        $("#logo_holder").contents().find("#logo").addClass("animated");
        // Add bottom overlay 
        $('<div id="top_overlay" class="animated"><div class="text-center"><img src="./dist/img/anim_logo.svg"/><h3>'+options.text+'</h3></div>').appendTo($('body')).addClass('dpl');
    }  

}

function loading_done() {
    clearInterval(loading_interval);

    // Reset title
    /*
    $('.navbar-brand').find('.tx').find('span').each(function() {
        $(this).html($(this).attr('data-src'));
    });
    */
    $("#logo_holder").contents().find("#logo").removeClass("animated");

    // Remove Overlay 
    $('#overlay').fadeOut(150, function() {$('#overlay').remove();})
    $('body').css('overflow','auto');
    $('#top_overlay').removeClass('dpl');
} 


$(function() {

    // Automatic loading message
    if($('.load_msg').length!=0) {
        loading({text:$('.load_msg').text(),overlay:true});
    }

})
 