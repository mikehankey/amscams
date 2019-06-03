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
        type: 'iframe' 
      });
});



