// Create Modal with cropper 
function create_modal_cropper(image) {
    var cropBoxData;
    var canvasData;
    var cropper;

    // Modal
    $('<div class="modal fade" id="cropper_modal" tabindex="-1" role="dialog">\
      <div class="modal-dialog" role="document">\
        <div class="modal-content">\
          <div class="modal-header">\
            <h5 class="modal-title" id="modalLabel">Cropper</h5>\
            <button type="button" class="close" data-dismiss="modal" aria-label="Close">\
              <span aria-hidden="true">×</span>\
            </button>\
          </div>\
          <div class="modal-body">\
            <div class="img-container">\
              <img id="image" src="'+image+'" alt="Picture" class="">\
            </div>\
          </div>\
          <div class="modal-footer">\
            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
          </div>\
        </div>\
      </div>\
    </div>').appendto('body');

    $('#cropper_modal').on('shown.bs.modal', function () {
        cropper = new Cropper(image, {
          autoCropArea: 0.5,
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
    });

    $('#cropper_modal').modal('show');
}


 

create_modal_cropper('/mnt/ams2/TMP/2019_03_06_06_47_25_000_010038-trim0072_23.png');