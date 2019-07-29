


    // Modal
    




    /*
    .,
        preview : {
            display: true,
            size : [100,100],
        }
        */


    
       var image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';
       var cursor_dim = 50;
       //$('<img id="frame_to_crop" src="'+image_src+'" alt="Frame to crop">').appendTo('body');
       
       $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
       <div class="modal-dialog modal-lg" style="max-width:1100px;">\
         <div class="modal-content">\
           <div class="modal-header">\
             <h5 class="modal-title" id="modalLabel">Frame cropper</h5>\
             <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
               <span aria-hidden="true">×</span>\
             </button>\
           </div>\
           <div class="modal-body">\
              <p>Select the area of the meteor location</p>\
              <img id="frame_to_crop" src="'+image_src+'" alt="Select the area of the meteor">\
              <div id="cropped-original"></div>\
              <div id="cropped-resized"></div>\
           </div>\
           <div class="modal-footer">\
             <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
           </div>\
         </div>\
       </div>\
     </div>').appendTo('body');

     $('#cropper_modal').modal('show');
        
   
       $('#frame_to_crop').rcrop({
           minSize : [50,50],
           maxSize: [50,50],
           preserveAspectRatio : true,
           preview : {
               display: true,
               size : [100,100],
               wrapper : '#custom-preview-wrapper'
           }
       });
       
       $('#frame_to_crop').on('rcrop-changed', function(){
           var srcOriginal = $(this).rcrop('getDataURL');
           var srcResized = $(this).rcrop('getDataURL', 50,50);
       
           $('#cropped-original').append('<img src="'+srcOriginal+'">');
           $('#cropped-resized').append('<img src="'+srcResized+'">');
       })
    
   