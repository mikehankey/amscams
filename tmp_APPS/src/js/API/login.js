var COOKIE_NAME = "APIa"          // Token Access
var USER_COOKIE_NAME = "APIu478"  // User info
var PAGE_MODIFIED = "AJIhgg"

// Test if already logged in 
function test_logged_in() {
   return readCookie(COOKIE_NAME); 
} 

function getTok() {
   return test_logged_in();
}

// Get User Info
function getUserInfo() {
   return readCookie(USER_COOKIE_NAME); 
}


// UI transformed after loggined (add delete buttons)
function add_login_stuff() {
    
   if($('.lgi').length==0) {
      // Add buttons
      $('.prevproc').each(function() {

         if(!$(this).hasClass('arc')) {
               $('<div class="btn-toolbar lgi">\
               <div class="d-flex justify-content-around">\
                  <a class="conf col btn btn-success btn-sm mr-2" title="Confirm Detection">Confirm</a>\
                  <a class="del col btn btn-danger btn-sm" title="Delete Detection"><i class="icon-delete"></i></a>\
               </div>\
            </div>').appendTo($(this))
         } 
      });
   }
   
   $('.lio').show();

   setup_delete_buttons();
   setup_confirm_buttons();
   
}

// Remove Login Stuff
function remove_login_stuff() {

   // Remove  Buttons
   $('.lgi').remove();
   $('.lio').hide();
   $('.prevproc').show();
   
   $('.toDel').removeClass('toDel');
   $('.toConf').removeClass('toConf');

   hide_bottom_action();

   // MAin Button
   $('#del_text').text('');
   $('#conf_text').text('');


}


// Remove Login Cookie
function logout() {
   eraseCookie(COOKIE_NAME); 
   eraseCookie(USER_COOKIE_NAME); 
}


// Update UI based on logged or not 
function loggedin() {
   if(test_logged_in()!==null) {

      // Logout Button
      $("a#login").text('Logout').unbind('click').click(function() {
         logout();
         loggedin();
      });

      // Add buttons
      add_login_stuff();
   } 
   else {
      $("a#login").text('Login');
      setup_login();
      remove_login_stuff();
   }        
}

// Add Login Modal
function add_login_modal() {
      // Add Login Modal
      if($('#login_modal').length==0) {
         $('<div id="login_modal" class="modal fade" tabindex="-1" role="dialog">\
            <div class="modal-dialog modal-dialog-centered" style="max-width:300px" role="document">\
            <div class="modal-content">\
            <div class="modal-header">\
            <h5 class="modal-title">Login to '+STATION+'</h5>\
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
               <span aria-hidden="true">&times;</span>\
            </button>\
            </div>\
            <div class="modal-body pb-4" >\
               <div class="d-flex justify-content-center form_container">\
                  <form>\
                     <input type="hidden" name="st" value="'+STATION+'"/>\
                     <div class="input-group mb-3">\
                        <input type="text" name="username" class="form-control input_user" value="" placeholder="username">\
                     </div>\
                     <div class="input-group mb-2">\
                        <input type="password" name="password" class="form-control input_pass" value="" placeholder="password">\
                     </div>\
                     <div class="d-flex justify-content-center mt-3 login_container">\
                        <button type="button" name="button" id="subm_login" class="btn btn-primary" style="width: 100%;">Login</button>\
                     </div>\
                  </form>\
               </div>\
            </div></div></div></div>').appendTo('body');
      }
}


// Create Login Modal
function setup_login() {
 
   // Login
   $('#login').unbind('click').click(function(e){
      e.stopImmediatePropagation(); 
 
      $('#login_modal').modal('show');

      $('#subm_login').click(function() {
            // So we can send the USR to the API
            var $t = $(this);
            var _data = {'function':'login', 'usr':$('input[name=username]').val(), 'pwd':$('input[name=password]').val(), 'st':stID};

            loading_button($t);
            $.ajax({ 
               url:   API_URL ,
               data: _data, 
               format: 'json',
               success: function(data) { 
                  data = jQuery.parseJSON(data); 
                     
                  load_done_button($t);

                  if(typeof data.error !== 'undefined') {
                     // WRONG!
                     bootbox.alert({
                        message: data.error,
                        className: 'rubberBand animated error',
                        centerVertical: true 
                     });
                     logout();
                  } else {

                     $('#login_modal').modal('hide'); 
                     createCookie(COOKIE_NAME,data.token,2/24)
                     createCookie(USER_COOKIE_NAME,_data['user']+'|'+_data['st'],2/24);
                     loggedin();    
                  } 
               }, 
               error:function() { 
                  load_done_button($t);
                  $('#login_modal').modal('hide');
                  bootbox.alert({
                     message: "Impossible to reach the API. Please, try again later.",
                     className: 'rubberBand animated error',
                     centerVertical: true 
                  });
                  logout();
                  loggedin();
               }
            });
      })

      return false;
   }) 
}     