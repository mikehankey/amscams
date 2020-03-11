

   // Takes care of the lazy carousels
   /*$(function() {
   $("#carousel").carousel().on("slide.bs.carousel", function(ev) {
       var lazy;
       lazy = $(ev.relatedTarget).attr('data-src');
       lazy.attr("src", lazy.data('src'));
       lazy.removeAttr("data-src");
     });
     
   });



   $("#carousel").on("slide.bs.carousel", function(ev) {
      var lazy;
      console.log("SLIDING");
      lazy = $(ev.relatedTarget).attr('data-src');
      console.log(lazy);
      lazy.attr("src", lazy.data('src'));
      lazy.removeAttr("data-src");
    }).carousel();*/



    $('#carouselWInd').carousel({'ride':'False'});

    $("#carouselWInd").on("slide.bs.carousel", function(ev) {
      var $img = $(ev.relatedTarget).find('img')
      var src  = $img.attr('data-src');
      $img.attr("src", src);
      $img.removeAttr("data-src");
    });