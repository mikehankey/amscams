function show_add_frame_modal() {

    if($('#add_frame_modal').length === 0) {
        // Create modal if not exist
        $('<div class="modal fade" id="add_frame_modal"><div class="modal-dialog modal-xl"><div class="modal-content"><div class="modal-header"><h5>Click "+" to select the position of the new frame to generate</h5> <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span>&times;</span></button></div><div class="modal-body"><div id="add_frame_container" class="d-flex flex-wrap"></div></div></div></div></div>').appendTo('body')
    }

    // By default we regenerate the whole content in case a frame has been added 
    $('#add_frame_container').html('');

}

function populate_frame_modal() {
    var frame_count = 0;
    var _html = "";
    var all_frame_ids = [];

    // Get All Frame Ids
    $('#reduc-tab tbody tr').each(function() {
        var cur_frame_number = $(this).attr('id');
        cur_frame_number = cur_frame_number.split('_');
        all_frame_ids.push(parseInt(cur_frame_number[1]));
    });
 
    console.log(all_frame_ids);
    
    $(all_frame_ids).each(function(ind, id) {
        var cl = "";
        var cur_fr_img  = $('tr#fr_'+id).find('img').clone(); 
        cur_fr_img.removeClass('select_meteor').css({width:'80px', height:'80px'})
        cur_frame_number = parseInt(id);
        
        if(frame_count==0) {
           // Add first "-" button
           if((cur_frame_number-1)>0) {
                _html += "<button class='btn btn-primary addf' data-rel='"+(cur_frame_number-1)+"'>+</button>";
           } else {
                _html += "<button style='opacity:.2' class='btn btn-primary addf' disabled data-rel='"+(cur_frame_number-1)+"'>+</button>";
           }
        }

        // Add Thumb and frame #
          // Every 8 thumb, we add a left margin 
        if(frame_count!=0 && frame_count % 8 ==0 ) {
            cl = "mgr";
        } else {
            cl = "";
        }

        _html += "<div class='fth "+cl+"'><span>#"+cur_frame_number+"</span>" + cur_fr_img.prop("outerHTML") + "</div>";
        
        // Add Button (+)
        cur_frame_number += 1;
        if(all_frame_ids.indexOf(cur_frame_number)==-1) {
            _html += "<button class='btn btn-primary addf' data-rel='"+cur_frame_number+"'>+</button>";
        } else {
            _html += "<button class='btn btn-primary addf' style='opacity:.2' disabled data-rel='"+cur_frame_number+"'>+</button>";
        }
       

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
