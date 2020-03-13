function setup_single_delete_buttons()  {
 
  $('.del.single').click(function() {

      bootbox.confirm({
         message: "You are about to delete this detection.<br/>Please, confirm.",
         centerVertical: true,
         buttons: {
            cancel: {
               label: 'No',
               className: 'btn-danger'
            },
            confirm: {
               label: 'Yes',
               className: 'btn-success'
            }
         },
         callback: function (result) {
            if(result) {   send_API_task({'toDel':cropped_video},'','');
            }
         }
      });
   
   });

}


// WARNING HERE WE SEND "CROPPED VIDEO" BECAUSE IT'S IN THE TEMPLATE
// AND WE KNOW IT'S UNIQUE FOR THE DETECTION
function setup_single_conf_buttons() {
   $('.conf.single').click(function() {
      send_API_task({'toConf':cropped_video},'','');
      return false;
   });
}