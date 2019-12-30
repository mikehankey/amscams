// This file uses update_url_param defined in pagination/per_page.js

$(function() {


   //Magnitude
   $('#mag').change(function() {
      // Change Meteor Per page
      new_url = update_url_param(window.location.href ,'magnitude',$('#mag').val());

      Cookies.set('filt_arch_mag', $('#mag').val(), { expires: 99999, path: '/' });

      // Back to page = 1 (so we dont have issues if the number of page is too mall)
      window.location =  update_url_param(new_url ,'p',1);
    });
   
   //Res Eror
   $('#res_error').change(function() {
      // Change Meteor Per page
      new_url = update_url_param(window.location.href ,'res_error',$('#res_error').val());
      
      Cookies.set('filt_arch_res_error', $('#res_error').val(), { expires: 99999, path: '/' });

      // Back to page = 1 (so we dont have issues if the number of page is too mall)
      window.location =  update_url_param(new_url ,'p',1);
    });


    //Magnitude
    $('#ang_vel').change(function() {
      // Change Meteor Per page
      new_url = update_url_param(window.location.href ,'ang_vel',$('#ang_vel').val());

      Cookies.set('filt_arch_ang_vel', $('#ang_vel').val(), { expires: 99999, path: '/' });

      // Back to page = 1 (so we dont have issues if the number of page is too mall)
      window.location =  update_url_param(new_url ,'p',1);
    });


    //Sync
    $('#sync').change(function() {
      // Change Meteor Per page
      new_url = update_url_param(window.location.href ,'sync',$('#sync').val());
 
      Cookies.set('filt_arch_sync', $('#sync').val(), { expires: 99999, path: '/' });

      // Back to page = 1 (so we dont have issues if the number of page is too mall)
      window.location =  update_url_param(new_url ,'p',1);
    });
})
