$(function() {

   // Click on json viewer button or link
   // open a modal with the json file 
   // friendly displayed :)
   $('.json_viewer').click(function() {

      var $t = $(this);
      json_path = $t.attr("data_src");

      //json_path = "/mnt/ams2/meteor_archive/AMS7/METEOR/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD.json";

      loading({text: "Retrieving JSON data..."});

      // Load the json via AJAX
      $.ajax({
         url: json_path,
         type: "GET",  
         success: function (data) {

            console.log(data);

            // We create the modal
            $('#json_modal').remove();

            $('<div id="json_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered modal-lg" role="document">\
            <div class="modal-content"><div class="modal-body"><div id="json-renderer" style="min-width: 800px;background: #fff;color: #000; font-family: monospace;" class="d-flex justify-content-between"><p><b>JSON</b></p>\
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