var STATION = "AMS7";
var API_URL = "https://sleaziest-somali-2255.dataplicity.io/pycgi/webUI.py?cmd=API";
var LOGGEDIN = false; // Just UI - the rest is managed on both side with a token
var TOK;
var USR;

function setup_action() {
   setup_login();
}
  
$(function() {
   setup_action();
})