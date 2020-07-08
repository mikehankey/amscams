function refresh_all_popups() {
   $('.img-link, .img-link-n').magnificPopup({
      type: 'image' ,
      removalDelay: 300, 
      mainClass: 'mfp-fade',
      gallery:{
       enabled:true
      },
      callbacks: {
       elementParse: function(item) {
         $('.mfp-img').css('width','700px')
       }
     }
    });


         
    $('.vid-link').magnificPopup({
       type: 'iframe',
       preloader: true
     });
    

    $('.img-link-gal').magnificPopup({
      type: 'image' ,
      mainClass: 'mfp-fade',
      gallery:{
        enabled:true
      }
    });


    $('.vid_link_gal').magnificPopup({
      type: 'iframe',
      preloader: true,
      gallery:{
        enabled:true
      },
      iframe: {
        markup: '<div class="mfp-iframe-scaler">'+
          '<div class="mfp-close"></div>'+
          '<iframe class="mfp-iframe" frameborder="0" allowfullscreen></iframe>TOTOTO'+
        '</div>',
         
      }
    });
}


$(function() {
   refresh_all_popups();
});



