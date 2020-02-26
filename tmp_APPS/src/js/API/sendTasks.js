function send_API_task(jsonData) {


   var usr = getUserInfo();
   usr = usr.split('|');

   $.ajax({ 
      url:   API_URL ,
      data: {'function':'tasks',  'tok':test_logged_in(), 'data': jsonData, 'usr':usr[0], 'st':usr[1]}, 
      format: 'json',
      success: function(data) { 
         data = jQuery.parseJSON(data); 
         if(typeof data.error !== 'undefined') {
            // WRONG!
            bootbox.alert({
               message: data.error,
               className: 'rubberBand animated error',
               centerVertical: true 
            });

            if(typeof data.log !== 'undefined' && data.log==1) {
               logout();
               loggedin();
            }
               
         }  
      }, 
      error:function() { 
         bootbox.alert({
            message: "Impossible to reach the API. Please, try again later or refresh the page and log back in",
            className: 'rubberBand animated error',
            centerVertical: true 
         });
      }
   });
}



function update_all() {

   // Send a list of task to the API
   $('#bottom_action_bar .btn').click(function() {

      var toDel = [], toConf = [], $toDel = [], $toConf = [], msg = "You are about to ", toDelB = false, toDelC = false;

      // Get All to delete
      $('.prevproc.toDel').each(function() {
         var $t = $(this);
         var path = $t.find('a.T>img').attr('src');
         toDel.push(path);
         $toDel.push($t);
         toDelB = true;
      });

      if(toDel.length>0) {
         if(toDel.length>1) {
            t = "detections"
         } else {
            t = "detection"
         }
         msg += " <b>delete " + toDel.length + " " + t + "</b>";
      }

      // Get All to confirm
      $('.prevproc.toConf').each(function() {
         var $t = $(this);
         var path = $t.find('a.T>img').attr('src'); 
         toConf.push(path);
         $toConf.push($t);
         toDelC = true;
      });

      if(toConf.length>0 ) {
         if(toConf) {
            msg += " and " ;
         }
         if(toConf.length>1) {
            t = "detections"
         } else {
            t = "detection"
         } 
         msg += " <b>confirm " + toConf.length + " " + t + "</b>";
      }

      if(toDel || toConf) {
         // Bootbox Confirm
         bootbox.confirm({
            message: msg + ".<br/>Please, confirm.",
            centerVertical: true,
            buttons: {
               confirm: {
                  label: 'Yes',
                  className: 'btn-success'
               },
               cancel: {
                  label: 'No',
                  className: 'btn-danger'
               }
            },
            callback: function (result) {
               if(result) {
                  send_API_task({'toDel':toDel,'toConf':toConf});
               }
            }
         });
      } 
   })
}



$(function() {
   update_all();
})