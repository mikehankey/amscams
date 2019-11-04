$(function() {

   $('#refresh_media').click(function() {
      update_url_param(window.location.href ,'clear_cache',1);
   })
})