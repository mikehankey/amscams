$(function() {

   // Takes care of the lazy carousels
   $("#carousel").carousel();
     return $("#carousel.lazy").on("slide", function(ev) {
       var lazy;
       lazy = $(ev.relatedTarget).find("img[data-src]");
       lazy.attr("src", lazy.data('src'));
       lazy.removeAttr("data-src");
     });
   });