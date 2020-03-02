$(function() {
      $('.img-link, .img-link-n').magnificPopup({
        type: 'image' ,
        removalDelay: 300, 
        mainClass: 'mfp-fade',
        gallery:{
         enabled:true
        },
        callbacks: {
         elementParse: function(item) {
           // Function will fire for each target element
           // "item.el" is a target DOM element (if present)
           // "item.src" is a source that you may modify
     
           console.log(item); // Do whatever you want with "item" object
         }
       }
      });


     
      

      $('.img-link-gal').magnificPopup({
        type: 'image' ,
        mainClass: 'mfp-fade',
        gallery:{
          enabled:true
        }
      });
      
      $('.vid-link').magnificPopup({
        type: 'iframe',
        preloader: true
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



