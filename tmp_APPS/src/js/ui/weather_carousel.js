// Carousel for NOAA
$(function() {
      $('#carouselWInd').addClass('carousel').carousel({'ride':'true','interval':0});

      $("#carouselWInd").on("slide.bs.carousel", function(ev) {
         var $img = $(ev.relatedTarget).find('img')
         var src  = $img.attr('data-src');
         $img.attr("src", src);
         $img.removeAttr("data-src");
      });
});