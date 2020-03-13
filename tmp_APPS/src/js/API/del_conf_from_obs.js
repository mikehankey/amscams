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
            if(result) {
   
   
               // /AMS7/DETECTS/PREVIEW/2019/2019_12_24/2019_12_24_11_39_19_000_010041-trim0074-prev-crop.jpg
   
               send_API_task({'toDel':cropped_video},'','');
            }
         }
      });
   
   })


   // 
}


function setup_remove_delete_buttons() {
   
}