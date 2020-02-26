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
      msg += " delete " + toDel.length + "detections";
   }

    // Get All to confirm
    $('.prevproc.toConf').each(function() {
      var $t = $(this);
      var path = $t.find('a.T>img').attr('src'); 
      toConf.push(path);
      $toConf.push($t);
      toDelC = true;
   });

   if(toDel.length>0 ) {
      if(toDelB) {
         msg += " and " ;
      }

      msg += " confirm " + toConf.length + "detections";
   }

   if(toDel || toConf) {
      // Bootbox Confirm
      bootbox.confirm({
         message: msg + ". Please, confirm.",
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
               console.log(toConf);
               console.log(toDel);
            }
         }
      });
   }


   


})