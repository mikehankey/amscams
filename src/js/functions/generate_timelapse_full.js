/**
 * Avoid the same position for watermark & info
 */

function avoid_same_location() {
    $('select[name=wat_pos],select[name=text_pos]').change(function(e) {
        var $src = $(e.target);
        var val = $src.val();
        var $dest;
        var v_dest;
        var v_src = $src.val();
        
        
        if($src.attr('name')=='wat_pos') {
            $dest = $('select[name=text_pos]')
        } else {
            $dest = $('select[name=wat_pos]')
        }

        v_dest = $dest.val();

        if(v_src==v_dest) {
            switch (v_src) {
                case "tr":
                  $dest.val("br");
                  break;
                case "tl":
                  $dest.val("br");
                  break;
                case "bl":
                  $dest.val("tr");
                  break;
                case "br":
                  $dest.val("bl");
                  break;
            }
        }  

    });
}
 



function add_timelapse_full_modal() {

    // Init date picker with current date
    var utcMoment = moment.utc();
    var curD = utcMoment.format('YYYY/MM/DD');

    // Get the Cam IDs for the select
    var cam_ids = $('input[name=cam_ids]').val();
    cam_ids = cam_ids.split('|');

    var cam_select = "<select id='sel_cams' name='sel_cam[]' class='form-control'  multiple='multiple'>";
    $.each(cam_ids,function(i,v){
        if($.trim(v)!=='') {
            if(i==0) sel = "selected"
            else sel = ""
            cam_select = cam_select + "<option "+ sel + " value='"+v+"'>Camera #" + v + "</option>";
        }
    });
    cam_select = cam_select + "</select>";


    $('#full_timelapse_modal').remove(); 
    $('<div id="full_timelapse_modal" class="modal" tabindex="-1" role="dialog"> \
        <div class="modal-dialog modal-dialog-centered modal-lg" role="document"> \
            <div class="modal-content"> \
            <div class="modal-header"> \
                <h5 class="modal-title">Generate Timelapse</h5> \
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"> \
                <span aria-hidden="true">&times;</span> \
                </button> \
            </div> \
            <div class="modal-body"> \
                <form id="timelapse_full_form"> \
                    <div class="pr-3 pl-3 pt-0"> \
                            <div class="form-group mb-2"> \
                                <label class="col-form-label"><b>Date</b></label> \
                                <div class="col-sm-3 p-0">\
                                    <input name="video_date" value="'+curD+'" type="text" data-display-format="YYYY/MM/DD" class="datepicker form-control"> \
                                </div>\
                            </div> \
                            <div class="form-group mb-2"> \
                                <label class="col-form-label"><b>Camera</b> <i>One video per camera</i></label> \
                                <div>'+cam_select+'</div> \
                            </div> \
                            <div class="row">\
                                <div class="col-sm-6">\
                                    <div class="form-group  mb-1"> \
                                        <label for="fps" class=" col-form-label"><b>FPS</b></label> \
                                            <select name="fps" class="form-control"> \
                                                <option value="1">1 fps</option> \
                                                <option value="5">5 fps</option> \
                                                <option value="10">10 fps</option> \
                                                <option value="15">15 fps</option> \
                                                <option value="23.976">23.976 fps</option> \
                                                <option value="24">24 fps</option> \
                                                <option value="25">25 fps</option> \
                                                <option value="29.97" >29.97 fps</option> \
                                                <option value="30" selected>30 fps</option> \
                                                <option value="50">50 fps</option> \
                                                <option value="59.94">59.94 fps</option> \
                                                <option value="60">60 fps</option> \
                                            </select> \
                                    </div> \
                                </div>\
                                <div class="col-sm-6">\
                                    <div class="form-group mb-2"> \
                                        <label for="dim" class="col-form-label"><b>Dimension</b></label> \
                                            <select name="dim" class="form-control"> \
                                                <option value="1920:1080">1920x1080</option> \
                                                <option value="1280:720" selected>1280x720</option> \
                                                <option value="640:320">640x320</option> \
                                            </select> \
                                    </div> \
                                </div>\
                            </div>\
                            <div class="row">\
                                <div class="col-sm-6">\
                                    <div class="form-group mb-2">\
                                        <label for="wat_pos" class="col-form-label"><b>Position of the AMS Watermark</b></label> \
                                            <select name="wat_pos" class="form-control"> \
                                                <option value="tr" >Top right</option> \
                                                <option value="tl" selected>Top Left</option> \
                                                <option value="br" >Bottom Right</option> \
                                                <option value="bl" >Bottom Left</option> \
                                            </select> \
                                    </div> \
                                </div>\
                                <div class="col-sm-6">\
                                    <div class="form-group mb-2"> \
                                        <label for="text_pos" class="col-form-label"><b>Position of the Camera Info</b></label> \
                                        <select name="text_pos" class="form-control"> \
                                            <option value="tr">Top right</option> \
                                            <option value="tl" >Top Left</option> \
                                            <option value="br" >Bottom Right</option> \
                                            <option value="bl" selected>Bottom Left</option> \
                                        </select> \
                                    </div>\
                                </div>\
                            </div> \
                            <div class="form-group mb-2">\
                                <label for="extra_text" class="col-form-label"><b>Extra info (added above the Camera Info)</b></label> \
                                <input type="text" name="extra_text" class="form-control" value=""/> \
                            </div>\
                        </div> \
                     </div> \
                </form> \
            <div class="modal-footer"> \
                <button type="button" id="generate_timelapse" class="btn btn-primary">Generate</button> \
                <button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button> \
            </div> \
        </div> \
        </div>').appendTo('body').modal('show');

    // Multi Select cam
    $('select#sel_cams').multiselect({includeSelectAllOption: true});
   
    //Start datepicker
    load_date_pickers();

    // Avoid Same Location
    avoid_same_location();
  
    // Date
    $('#tl_date').val($('input[name=cur_date]').val());

    // Init duration
    $('#tld').val(parseFloat($('#tot_f').val()/parseFloat($('select[name=fps]').val())).toFixed(2) + ' seconds');

    // Update duration 
    $('select[name=fps]').unbind('change').bind('change',function() {
        $('#tld').val(parseFloat($('#tot_f').val()/parseFloat($(this).val())).toFixed(2) + ' seconds');
    });

    // Generate
    $('#generate_timelapse').click(function() { 
        var cmd_data = JSON.stringify( $("#timelapse_full_form").serializeArray() ); //getFormData($("#timelapse_full_form"));
        cmd_data.cmd = "generate_timelapse";

 
        $('#full_timelapse_modal').modal('hide');
        loading({text: "Creating Video", overlay: true});
        
        $.ajax({ 
            url:  "/pycgi/webUI.py",
            data: cmd_data,
            success: function(data) {
                var json_resp = $.parseJSON(data); 
                bootbox.alert({
	                message: json_resp.msg,
	                className: 'rubberBand animated',
	                centerVertical: true
                });
                loading_done();
            }, 
            error:function(err) {
                bootbox.alert({
	                message: "The process returned an error - please try again later",
	                className: 'rubberBand animated error',
	                centerVertical: true
                });
                
                loading_done();
            }
        });
    });
}

$(function() {
    $('#create_timelapse').click(function() {
        add_timelapse_full_modal();    
    });
})