function HD_fix() {

   bootbox.confirm({
      message: "Use this function if the meteor doesnt appear in the HD video (and the HD Stack). The HD video will be replaced by a resized version of the SD video.",
      className: 'rubberBand animated info',
      centerVertical: true,
      buttons: {
         cancel: {
             label: 'Cancel'
         },
         confirm: {
             label: 'Continue'
         }
     },
     callback: function (result) {
      console.log('This was logged in the callback: ' + result);
      }
   });
}

$(function() {
   $('#hd_fix').click(function() {
      HD_fix();
   })
})
