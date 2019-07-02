function add_timelapse_modal() {
    $('#timelapse_modal').remove();

    $('<div id="timelapse_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" role="document">\
    <div class="modal-content"><div class="modal-body"><div id="anim_header" class="d-flex justify-content-between"><p><b>Generate Timelapse</b></p><p><span id="tot_f"></span> frames</p></div><div id="anim_holder" style="height:326px">\
    </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2">\
    <button type="button" class="btn btn-primary" data-dismiss="modal">Generate</button><button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button></div></div></div></div>').appendTo('body');

    // How many frames 
    $hmf = $('img.lz');
    
}

$('#create_night_anim').click(function() {

});