$(function() {

   // Click on json viewer button or link
   // open a modal with the json file 
   // friendly displayed :)
   $('.json_viewer').click(function() {

      var $t = $(this);
      json_path = $t.attr("data_src");
 

      loading({text: "Retrieving JSON data..."});

      // Load the json via AJAX
      $.ajax({
         url: json_path,
         type: "GET",  
         success: function (data) {

         
            // We create the modal
            $('#json_modal').remove();

            $('<div id="json_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered modal-lg" role="document">\
            <div class="modal-content"><div class="modal-body"><h5><a href="'+json_path+'" target="_blank">JSON File <sup><span class="icon-new-window"></span></sup></a></h5><div id="json-renderer"><p><b>JSON</b></p>\
            </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2"></div>\
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');

            $('#json_modal').modal('show');
            $('#json-renderer').jsonViewer(data);  

            loading_done();
         }, 
         error: function(e) {
           bootbox.alert({
               message: "Impossible to retrieve the JSON DATA",
               className: 'rubberBand animated error',
               centerVertical: true 
           });
           loading_done();
         }  
      });
   });

})