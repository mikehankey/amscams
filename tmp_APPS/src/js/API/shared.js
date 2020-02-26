var STATION = "AMS7";
var API_URL = "https://sleaziest-somali-2255.dataplicity.io/pycgi/webUI.py?cmd=API";
  
function setup_action() {
   setup_login();
}



  
$(function() {

   // We test if the page has already been updated within the hour
   if(readCookie(PAGE_MODIFIED)!=null && readCookie(PAGE_MODIFIED)==window.location.href) {
      $('<div class="alert alert-info"><span class="icon-notification"></span> <b>You have already made edits for this page within the last hour. Please allow for at least one hour for changes to take effect.</b></div>').prependTo('#main_container');
   }

   add_login_modal();
   setup_action();

   // Test if we are loggedin
   loggedin();
   check_bottom_action();
})