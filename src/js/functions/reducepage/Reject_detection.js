function reject_detection_from_archive(detections) {
   msg = "Are you sure you want to PERMANENTLY delete this detection?";
   bootbox.confirm(msg, function(result){ 
      if(result) {
         // Deleting
         
         loading({'text': 'Moving the detection to Trash'});

         $.ajax({ 
               type:"POST",
               url:  "webUI.py?cmd=delete_archive_multiple_detection",
               data: {detections: [detections]},
               success: function(data) { 
                  loading_done();
                  window.location.reload();   
               }, 
               error: function() {
                     alert('Impossible to reject. Please, reload the page and try again later.')
                     loading_done();
               }
         });
      }  
   });

}


function reject_detection(json_file) { 
 
   var detections = [];  
   var ids = [];
   detections.push(json_file);
   

   reject_detection_from_archive(detections);
}




$(function() {
   $('#reject_detection').click(function() {
      reject_detection(json_file); // json_file is defined in the page
   })
})