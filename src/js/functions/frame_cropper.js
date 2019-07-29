    
       var image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';
       var cursor_dim = 50; 
       
       $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
       <div class="modal-dialog modal-lg" style="max-width:1300px">\
         <div class="modal-content">\
           <div class="modal-header">\
             <h5 class="modal-title" id="modalLabel">Frame cropper</h5>\
             <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
               <span aria-hidden="true">×</span>\
             </button>\
           </div>\
           <div class="modal-body">\
              <p>Select the area of the meteor location</p>\
              <div>\
                <div id="selector" style="width:50px; heigth:50px; border:2px solid #fff"></div>\
                <img id="frame_to_crop" src="'+image_src+'" alt="Select the area of the meteor" class="img-fluid" >\
              </div>\
           </div>\
           <div class="modal-footer">\
             <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
           </div>\
         </div>\
       </div>\
     </div>').appendTo('body');

     $('#cropper_modal').modal('show'); 
   




     $( "#selector" ).draggable({ containment: "parent" });