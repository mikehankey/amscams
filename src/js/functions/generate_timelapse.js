function add_timelapse_modal() {
    $('#timelapse_modal').remove();

    


    $('<div class="modal" tabindex="-1" role="dialog"> \
        <div class="modal-dialog modal-dialog-centered modal-lg" role="document"> \
            <div class="modal-content"> \
            <div class="modal-header"> \
                <h5 class="modal-title">Generate Timelapse</h5> \
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"> \
                <span aria-hidden="true">&times;</span> \
                </button> \
            </div> \
            <div class="modal-body"> \
                <form> \
                    <div class="form-group row mb-1"> \
                        <label class="col-sm-2 col-form-label"><b>Frame Count</b></label> \
                        <div class="col-sm-10"> \
                            <input type="text" readonly class="form-control-plaintext" id="tot_f" value=""> \
                        </div> \
                    </div> \
                    <div class="form-group row mb-1"> \
                        <label for="dim">Dimension</label> \
                        <div class="col-sm-10"> \
                            <select id="dim" class="form-control"> \
                                <option value="dim1">1920x1080</option> \
                                <option value="dim2">1280x720</option> \
                                <option value="dim3">640x320</option> \
                            </select> \
                        </div> \
                    </div> \
                </form> \
            </div> \
            <div class="modal-footer"> \
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button> \
                <button type="button" class="btn btn-primary">Generate</button> \
            </div> \
            </div> \
        </div> \
        </div>').appendTo('body').modal('show');

    // How many frames 
    hmf = $('img.lz').not('.process').length;
    $('#tot_f').val(hmf);

}

$(function() {
    $('#create_night_anim').click(function() {
        add_timelapse_modal();
    });
})