var STATION = "AMS7";
var API_URL = "https://sleaziest-somali-2255.dataplicity.io/pycgi/webUI.py?cmd=API";
  
function setup_action() {
   setup_login();
}
  
$(function() {
   add_login_modal();
   setup_action();
})