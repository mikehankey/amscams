
// Modal for selector
function addModalTemplate() {
    if($('#select_meteor_modal').length==0) {
        $('<div id="select_meteor_modal" class="modal fade" tabindex="-1"><input type="hidden" name="thumb_w"/><input type="hidden" name="thumb_h"/><div class="modal-dialog  modal-lg modal-dialog-centered" role="document"><div class="modal-content"><div class="modal-body"><button title="Next" type="button" class="mfp-arrow mfp-arrow-right mfp-prevent-close"></button><button title="Prev" type="button" class="mfp-arrow mfp-arrow-left mfp-prevent-close"></button><p><strong>FRAME #<span id="sel_frame_id"></span> - Click the center of the meteor.</strong> <span id="meteor_org_pos" class="float-right pl-3"><b>Org:</b></span> <span id="meteor_pos" class="float-right"></span></p><div class="meteor_chooser"><div id="org_lh"></div><div id="org_lv"></div><div id="lh"></div><div id="lv"></div></div></div><div class="modal-footer p-0 pb-2 pr-2"><button type="button" class="btn btn-primary" id="Save Meteor Center">Save</button><button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
    }
}

// Actions on modal 
function setup_modal_actions(x,y) {

    // Warning: preview  = 400x400
    //    thumb real dim = 100x100
    x = parseInt(x);
    y = parseInt(y);

    // Update Info
    $('#meteor_org_pos').html('<b>Org:</b> '+x+'/'+y);
    $('#meteor_pos').text(x+'/'+y);

    $(".meteor_chooser").unbind('click').click(function(e){
        var parentOffset = $(this).offset(); 
        var relX = parseFloat(e.pageX - parentOffset.left);
        var relY = parseFloat(e.pageY - parentOffset.top);

        // Transform values
        if(!$(this).hasClass('done')) {
            $(this).addClass('done');
        } else {
            $('#lh').css('top',relY);
            $('#lv').css('left',relX);
            $('#meteor_pos').text(parseInt(relX+x)+'/'+parseInt(relY+y));
        }
    }).unbind('mousemove').mousemove(function(e) {
        var parentOffset = $(this).offset(); 
        var relX = e.pageX - parentOffset.left;
        var relY = e.pageY - parentOffset.top;
        // Cross
        if(!$(this).hasClass('done')) {
            $('#lh').css('top',relY);
            $('#lv').css('left',relX);
            $('#meteor_pos').text(parseInt(relX+x)+'/'+parseInt(relY+y));
        }
    });
}


function setup_select_meteor() {
    var viewer_dim = 400;
    var all_frames_ids = [];

    // Get all the frame ids
    $('#reduc-tab table tbody tr').each(function() {
        var id = $(this).attr('id');
        id = id.split('_');
        all_frames_ids.push(id[1]);
    });

    // Click on selector (button & thumb)
    $('.select_meteor').click(function() {
        var $tr = $(this).closest('tr');

        // Get meteor id
        var meteor_id = $tr.attr('id');
        meteor_id = meteor_id.split('_')[1];
      
        // Get Image
        var $img = $tr.find('img'); 

        var real_width, real_height;

        // Add template if necessary
        addModalTemplate();

        // Add image 
        $('.meteor_chooser').css('background-image','url('+$img.attr('src')+')');

        // Add current ID
        $('#sel_frame_id').text(meteor_id);


        // Update image real dimensions 
        var img = new Image();
        var imgSrc = $img.attr('src');

        $(img).on('load',function () {
            real_width = img.width;
            real_height = img.height;
            $('input[name=thumb_w]').val(real_width);
            $('input[name=thumb_h]').val(real_height); 
            // garbage collect img
            delete img;

            // Redefine viewer depending on the thumb dimension
            if(real_width !== real_height) {
            
                if(real_width > real_height) {
                    console.log('1');
                    $('.meteor_chooser').css('height',  real_height/real_width * viewer_dim);
                } else {
                    
                    console.log('2');
                    $('.meteor_chooser').css('width', real_width/real_height * viewer_dim);
                }

            } else {

                console.log('SAME');
                $('.meteor_chooser').css({'height': viewer_dim + 'px', 'width':viewer_dim + 'px'});
            }
            
            
            // Reset Cross position
            $('#lh').css('top','50%');
            $('#lv').css('left','50%');
            
            // Open Modal
            $('#select_meteor_modal').modal('show');
    
            // Reset
            $(".meteor_chooser").removeClass('done');

            setup_modal_actions($tr.attr('data-pos-x'),$tr.attr('data-pos-y'));
        
        }).attr({ src: imgSrc }); 

        

    });
}

 