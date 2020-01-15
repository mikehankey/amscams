// This file uses update_url_param defined in pagination/per_page.js

$(function() {

   

   $('#apply_archive_filters').click(function() {

      new_url = window.location.href
      
      if($('#mag').val()>=0) { 
         new_url = update_url_param(new_url ,'magnitude',$('#mag').val());
      } else {
         new_url = delete_url_param(new_url ,'magnitude');
      }

      if($('#res_er').val()>=0) { 
         new_url = update_url_param(new_url ,'res_er',$('#res_er').val());
      } else {
         new_url = delete_url_param(new_url ,'res_er');
      }

      if($('#ang_v').val()>=0) { 
         new_url = update_url_param(window.location.href ,'ang_v',$('#ang_v').val());
      } else {
         new_url = delete_url_param(new_url ,'ang_v');
      }

      if($('#sync').val()>=0) { 
         new_url = update_url_param(window.location.href ,'sync',$('#sync').val());
      } else {
         new_url = delete_url_param(new_url ,'sync');
      }

      if($('#point_score').val()>=0) { 
         new_url = update_url_param(window.location.href ,'point_score',$('#point_score').val());
      } else {
         new_url = delete_url_param(new_url ,'point_score');
      }

      if($('#multi').val()>=0) { 
         new_url = update_url_param(window.location.href ,'multi',$('#multi').val());
      } else {
         new_url = delete_url_param(new_url ,'multi');
      }
      
      console.log(update_url_param(new_url ,'p',1))
       // Back to page = 1 (so we dont have issues if the number of page is too mall)
       //window.location =  update_url_param(new_url ,'p',1);
   });
 
})
