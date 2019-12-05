function HD_fix() {

   bootbox.alert({
      message: "Use this function if the meteor doesnt appear in the HD video (and the HD Stack). The HD video will be replaced by a resized version of the SD video.",
      className: 'rubberBand animated info',
      centerVertical: true,
      buttons: {
         cancel: {
             label: '<i class="fa fa-times"></i> Cancel'
         },
         confirm: {
             label: '<i class="fa fa-check"></i> Continue'
         }
     }
   });
}

$(function() {
   $('#hd_fix').click(funtion() {
      HD_fix();
   })
})
