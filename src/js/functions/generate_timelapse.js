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
                        <div class="col-sm-4"> \
                            <input type="text" readonly class="form-control-plaintext" id="tot_f" value=""> \
                        </div> \
                    </div> \
                    <div class="form-group row mb-1"> \
                        <label class="col-sm-2 col-form-label"><b>Duration</b></label> \
                        <div class="col-sm-4"> \
                            <input type="text" readonly class="form-control-plaintext" id="tld" value=""> \
                        </div> \
                    </div> \
                    <div class="form-group row mb-1"> \
                        <label for="fps" class="col-sm-2 col-form-label"><b>FPS</b></label> \
                        <div class="col-sm-4"> \
                            <select id="fps" class="form-control"> \
                                <option value="1">1 fps</option> \
                                <option value="5">5 fps</option> \
                                <option value="10" selected>10 fps</option> \
                                <option value="15">15 fps</option> \
                                <option value="24.975">24.975 fps</option> \
                                <option value="29.97">29.97 fps</option> \
                                <option value="54.94">54.94 fps</option> \
                            </select> \
                        </div> \
                    </div> \
                    <div class="form-group row mb-1"> \
                        <label for="dim" class="col-sm-2 col-form-label"><b>Dimension</b></label> \
                        <div class="col-sm-4"> \
                            <select id="dim" class="form-control"> \
                                <option value="dim1">1920x1080</option> \
                                <option value="dim2" selected>1280x720</option> \
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

    // Init duration

    // Update duration 
    $('#fps').unbind('change').bind('change',function() {
        $('#tld').text(parseFloat($('#tot_f').val()/parseFloat($(this).val())).toFixed(2) + ' seconds');
    });
}

$(function() {
    $('#create_night_anim').click(function() {
        add_timelapse_modal();
    });
})