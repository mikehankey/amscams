function setup_single_delete_buttons()  {
 
  $('.delSingle').click(function() {

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
   $('.confSingle').click(function() {
      loading_button($(this));
      $(this).attr('disabled','disabled');
      send_API_task({'toConf':cropped_video},'','',function() { $('.confSingle').attr('data-init','Confirmed'); load_done_button($('.confSingle'));});
      return false;
   });
}