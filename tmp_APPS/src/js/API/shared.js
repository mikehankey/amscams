var STATION = "AMS7";
var API_URL = "http://archive.allsky.tv/APPS/API";
 
  
function setup_action() {
   setup_login();
}

function already_done() {

   // We test if the page has already been updated within the hour
   if(readCookie(PAGE_MODIFIED)!=null && readCookie(PAGE_MODIFIED)==window.location.href && $('#dejavu').length==0) {
      $('<div id="dejavu" class="alert alert-danger m-4" style="font-size: 1.2rem; text-align: center;"><span class="icon-notification"></span> <b>You have already made edits for this page within the last hour. Please allow for at least one hour for changes to take effect.</b></div>').insertBefore('#main_container');
       
      // Disabled buttons (only on daily report??)
      /*
      $('.prevproc  .btn').attr('disabled','disabled');
      $('.control-group .btn').removeAttr('disabled');
      $('.btn.conf, .btn.del').attr('disabled','disabled').addClass('disabled');
      */
   }
}

  
$(function() {

   add_login_modal();
   setup_action();

   // Test if we are loggedin
   loggedin();
   check_bottom_action();

   // Check if we can do something on this page
   already_done(); 
})