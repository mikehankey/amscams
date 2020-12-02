function loading(options) {

   $('body').css({'cursor':'wait'});

    // Avoir multiple loader
    if(options == undefined || options.standalone == undefined) {
       $('#bottom_overlay').remove();
       loading_done();  
    }
    
    if(options == undefined) {
        options = {
            text: 'Loading',
            overlay: true,
            container: 'body'       
        };
    } else {
        if(options.text == undefined)       options.text = 'Loading';
        if(options.overlay == undefined)    options.overlay = true;
        if(options.container == undefined)  options.container = 'body';
    }
    
    $("#logo_holder").contents().find("#logo").addClass("animated");

    // Overlay Option Container
    if(options.container !== undefined && options.overlay === true) {

        if(options.container !== undefined && options.container != 'body') { 
            $('<div class="overlay_loader" style="position: absolute;z-index: 9999;" class="animated"><div class="row h-100 text-center"><div class="col-sm-12 my-auto"><div class="card card-block" style="background:transparent"><iframe style="border:0;margin: 0 auto;" src="/dist/img/anim_logo.svg" width="140" height="90"></iframe><h4>'+options.text+'</h4></div></div></div></div>').appendTo(options.container);
        } else {
            $('body').css('overflow','hidden'); 
            $('<div id="overlay" class="animated"><div class="row h-100 text-center"><div class="col-sm-12 my-auto"><div class="card card-block" style="background:transparent"><iframe style="border:0;margin: 0 auto;" src="/dist/img/anim_logo.svg" width="140" height="90"></iframe><h4>'+options.text+'</h4></div></div></div></div>').appendTo('body');
        }  

    } else {
        // Add bottom overlay 
        $('<div id="bottom_overlay"><div class="text-center animated"><img src="/dist/img/anim_logo.svg"/><h3>'+options.text+'</h3></div>').appendTo($('body')).addClass('dpl');
    }  
 

}




function loading_done() {
    // Reset title
    /*
    $('.navbar-brand').find('.tx').find('span').each(function() {
        $(this).html($(this).attr('data-src'));
    });
    */
    $("#logo_holder").contents().find("#logo").removeClass("animated");

    // Remove Overlay(s)
    // I know, it doesn't make sense but my instructions are pretty vague 
    // and it's hard to follow so, please dont judge me too quickly
    $('#overlay').each(function() {
        $(this).fadeOut(150, function() {$('#overlay').remove();})
    });
    $('body').css('overflow','auto').css({'cursor':'default'});
    $('#bottom_overlay').removeClass('dlp').remove();  
} 


$(function() {

    // Automatic loading message
    if($('.load_msg').length!=0) {
        loading({text:$('.load_msg').text(),overlay:true});
    }

})
 
