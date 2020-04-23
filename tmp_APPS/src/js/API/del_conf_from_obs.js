function setup_single_delete_buttons()  {
 
  $('.delSingle').click(function() {

      // Video Path
      var video_API_path = cropped_video.replace(/^.*[\\\/]/, '');
      video_API_path = video_API_path.replace('-prev-crop.jpg','');
      video_API_path = video_API_path.replace('-HD-cropped.mp4','');

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
            if(result) { send_API_task({'toDel':video_API_path},'','', function(){});
            }
         }
      });
   
   });

}


// WARNING HERE WE SEND "CROPPED VIDEO" BECAUSE IT'S IN THE TEMPLATE
// AND WE KNOW IT'S UNIQUE FOR THE DETECTION
function setup_single_conf_buttons() {
   $('.confSingle').click(function() {
         var video_API_path = cropped_video.replace(/^.*[\\\/]/, '');
         video_API_path = video_API_path.replace('-prev-crop.jpg','');
         video_API_path = video_API_path.replace('-HD-cropped.mp4','');
         $(this).loading_button();
         $(this).attr('disabled','disabled');
         send_API_task({'toConf':video_API_path},'','', function() { $('.confSingle').attr('data-init','<i>✔</i> Confirmed'); 
         $('.confSingle').load_done_button();
         });
      return false;
   });
}