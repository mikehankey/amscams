$(function() {
    $('.img-link').magnificPopup({
        type: 'image' ,
        removalDelay: 300, 
        mainClass: 'mfp-fade'
      });
      
      $('.vid-link').magnificPopup({
        type: 'iframe',
        preloader: true,

        callbacks: {
          open: function() {
            $('.mfp-iframe').contents().find('video').attr('loop','');
          } 
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
});



