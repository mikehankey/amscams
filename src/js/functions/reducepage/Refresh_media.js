$(function() {

   $('#refresh_media').click(function() {
      window.location =  update_url_param(window.location.href ,'clear_cache',1);
   })
})