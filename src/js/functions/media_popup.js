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
        gallery:{
          enabled:true,
          preload: [0,2],     
          navigateByImgClick: true,
          arrowMarkup: '<button title="%title%" type="button" class="mfp-arrow mfp-arrow-%dir%"></button>', // markup of an arrow button
          tPrev: 'Previous (Left arrow key)', // title for left button
          tNext: 'Next (Right arrow key)', // title for right button
          tCounter: '<span class="mfp-counter">%curr% of %total%</span>' // markup of counter
        }
      });
});



