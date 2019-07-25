image_src = '/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png';


    var cropBoxData;
    var canvasData;
    var cropper;
    var image;

    // Modal
    $('<div class="modal fade" id="cropper_modal" tabindex="-1">\
      <div class="modal-dialog modal-lg" style="max-width: 1200px;">\
        <div class="modal-content">\
          <div class="modal-header">\
            <h5 class="modal-title" id="modalLabel">Frame cropper</h5>\
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
              <span aria-hidden="true">×</span>\
            </button>\
          </div>\
          <div class="modal-body">\
            <div class="img-container">\
              <img id="frame_to_crop" src="'+image_src+'" alt="Frame to crop" class="">\
            </div>\
          </div>\
          <div class="modal-footer">\
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
          </div>\
        </div>\
      </div>\
    </div>').appendTo('body');

    var image = document.getElementById('frame_to_crop');

    $('#cropper_modal').on('shown.bs.modal', function () {
        cropper = new Cropper(image, {
            dragMode: 'move',
            aspectRatio: 1 / 1, 
            restore: false,
            minCropBoxWidth: 50,
            maxCropBoxHeight: 50,
            guides: true,
            center: false,
            highlight: false,
            cropBoxMovable: true,
            cropBoxResizable: false,
            toggleDragModeOnDblclick: false,
          ready: function () {
            //Should set crop box data first here
            cropper.setCropBoxData(cropBoxData).setCanvasData(canvasData);
          }
        });
      }).on('hidden.bs.modal', function () {
        cropBoxData = cropper.getCropBoxData();
        canvasData = cropper.getCanvasData();
        cropper.destroy();
      });


    $('#cropper_modal').modal('show');


 