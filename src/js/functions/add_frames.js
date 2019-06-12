function show_add_frame_modal() {

    if($('#add_frame_modal').length === 0) {
        // Create modal if not exist
        $('<div class="modal fade" id="add_frame_modal"><div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5>Click "+" to select the position of the new frame to generate</h5></div><div class="modal-body"><div id="add_frame_container" class="d-flex flex-wrap"></div></div></div></div></div>').appendTo('body')
    }

    // By default we regenerate the whole content in case a frame has been added 
    $('#add_frame_container').html('');

}

function populate_frame_modal() {
    var frame_count = 0;
    var _html = "";
    $('#reduc-tab tbody tr').each(function() {

        var cur_fr_img  = $(this).find('img').clone(); 
        cur_fr_img.removeClass('select_meteor').css({width:'80px', height:'80px'})
        var cur_frame_number = $(this).attr('id');
        cur_frame_number = cur_frame_number.split('_');
        cur_frame_number = cur_frame_number[1];
        
        if(frame_count==0) {
           // Add first "-" button
           _html += "<button class='btn btn-secondary'>+</button>";
        }

        // Add Thumb and frame #
        _html += "<div class='fth'><span>#"+cur_frame_number+"</span>" + cur_fr_img.prop("outerHTML") + "</div>";
  
        // Add Button (+)
        _html += "<button class='btn btn-secondary addf'>+</button>";

        frame_count++;

    });

    $('#add_frame_container').html(_html).find('.select_meteor').removeClass('select_meteor');

}



function setup_add_frames() {
    $('#add_reduc_frame').unbind('click').click(function() {
        show_add_frame_modal();
        populate_frame_modal();
    });
}



show_add_frame_modal();
populate_frame_modal();
$('#add_frame_modal').modal('show');
