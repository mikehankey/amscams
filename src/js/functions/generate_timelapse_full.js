/**
 * Get the form values
 */
$.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name]) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


/**
 * Avoid the same position for watermark & info & extra logo
 */

function avoid_same_location() {
    $('select[name=wat_pos],select[name=text_pos],select[name=logo_pos]').change(function(e) {

        // Which one just changed?
        var $src = $(e.target);
        var v_src = $src.val(); 
        
        var $dest,$dest2;
        var v_dest,v_dest2;
        
        if($src.attr('name')=='wat_pos') {
            $dest = $('select[name=text_pos]');
            $dest2 = $('select[name=logo_pos]');
        } else if($src.attr('name')=='text_pos'){
            $dest = $('select[name=wat_pos]');
            $dest2 = $('select[name=logo_pos]');
        } else if($src.attr('name')=='logo_pos'){
            $dest = $('select[name=wat_pos]');
            $dest2 = $('select[name=text_pos]');
        }

        v_dest = $dest.val();
        v2_dest = $dest2.val();



        if(v_src==v_dest || v_src==v2_dest) {
            switch (v_src) {
                case "tr":
                  $dest.val("br");
                  $dest2.val("tl");
                  break;
                case "tl":
                  $dest.val("br");
                  $dest2.val("tr");
                  break;
                case "bl":
                  $dest.val("tr");
                  $dest2.val("tl");
                  break;
                case "br":
                  $dest.val("bl");
                  $dest2.val("tr");
                  break;
            }
        }  

    });
}



/**
 * Extra Logo selector
 */
function extra_logo_selector() {
    $('a.logo_selectable').click(function() {
        $('.logo_selectable').removeClass('selected');
        $(this).addClass('selected');
        $('select[name=logo]').val($(this).find('img').attr('src'));
    });
}


/**
 * Actions for extra logo
 */
function add_custom_logo() {
    $('select[name=extra_logo_yn]').change(function() {
         if($(this).val()=='y') {
            $('#position .col-sm-6').removeClass('col-sm-6').addClass('col-sm-4');
            $('#logo_pos, #logo_picker').removeAttr('hidden');
            
            // Populate select[name=logo] with logos
            if($('select[name=logo] option').length==0) {
                var all_logos = $('input[name=logos]').val();
                all_logos = all_logos.split('|');
                var $preview =  '<ul class="logo_selector">';
                $.each(all_logos,function(i,v){
                    if($.trim(v)!='') {
                        $('<option value="'+v+'">'+v+'</option').appendTo($("select[name=logo]"));
                        $preview += '<li><a class="logo_selectable"><img class="img-fluid ns" src="'+v+'"/></a><li>';
                    }
                })

                // Add Preview
                $preview += '</ul>';
                $('#logo_preview').html($preview);

                // Selectable
                extra_logo_selector();

                // Select default
                $('.logo_selector img[src="'+$('select[name=logo]').val()+'"]').closest('a').addClass('selected');
                
            }
      
        } else {
            $('#position .col-sm-4').removeClass('col-sm-4').addClass('col-sm-6');
            $('#logo_pos, #logo_picker').attr('hidden','hidden');
        }
    })
}



function add_timelapse_full_modal() {

    // Init date picker with current date
    var utcMoment = moment.utc();
    var curD = utcMoment.format('YYYY/MM/DD');

    var delete_after_days = $('input[name=delete_after_days]').val();

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
                <div class="alert alert-info"><span class="icon-notification"></span> The videos will be automatically deleted after  ' + delete_after_days + ' days</div> \
                <form id="timelapse_full_form"> \
                    <div class="pr-3 pl-3 pt-0"> \
                            <div class="form-group mb-2"> \
                                <label class="col-form-label"><b>Date</b></label> \
                                <div class="col-sm-3 p-0">\
                                    <input name="tl_date" value="'+curD+'" type="text" data-display-format="YYYY/MM/DD" class="datepicker form-control"> \
                                </div>\
                                <div class="col-sm-3 p-0">\
                                    <input name="tl_start_dime" value="'+curD+' 00:00" type="text" data-display-format="yyyy-mm-dd hh:ii" class="datepicker form-control"> \
                                </div>\
                            </div> \
                            <div class="form-group mb-2"> \
                                <label class="col-form-label"><b>Camera</b> <i>One video per camera</i></label> \
                                <div>'+cam_select+'</div> \
                            </div> \
                            <hr class="w"/>\
                            <p class="mt-3">The parameters below will be saved as default parameters for all automatically generated timelapse</p>\
                            <div class="row">\
                                <div class="col-sm-4">\
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
                                                <option value="30">30 fps</option> \
                                                <option value="50">50 fps</option> \
                                                <option value="59.94">59.94 fps</option> \
                                                <option value="60">60 fps</option> \
                                            </select> \
                                    </div> \
                                </div>\
                                <div class="col-sm-4">\
                                    <div class="form-group mb-2"> \
                                        <label for="dim" class="col-form-label"><b>Dimension</b></label> \
                                            <select name="dim" class="form-control"> \
                                                <option value="1920:1080">1920x1080</option> \
                                                <option value="1280:720">1280x720</option> \
                                                <option value="640:360">640x360</option> \
                                            </select> \
                                    </div> \
                                </div>\
                                <div class="col-sm-4">\
                                    <div class="form-group mb-2"> \
                                        <label for="dim" class="col-form-label"><b>Extra Logo</b></label> \
                                            <select name="extra_logo_yn" class="form-control"> \
                                                <option value="n" >No</option> \
                                                <option value="y" >Yes</option> \
                                            </select> \
                                    </div> \
                                </div>\
                            </div>\
                            <div class="row" id="position">\
                                <div class="col-sm-6" >\
                                    <div class="form-group mb-2">\
                                        <label for="wat_pos" class="col-form-label"><b>Position of the AMS Logo</b></label> \
                                            <select name="wat_pos" class="form-control"> \
                                                <option value="tr" >Top right</option> \
                                                <option value="tl" >Top Left</option> \
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
                                            <option value="bl" >Bottom Left</option> \
                                        </select> \
                                    </div>\
                                </div>\
                                <div id="logo_pos" class="col-sm-6" hidden>\
                                    <div class="form-group mb-2"> \
                                        <label for="logo_pos" class="col-form-label"><b>Position of the Logo</b></label> \
                                        <select name="logo_pos" class="form-control"> \
                                            <option value="tr" >Top right</option> \
                                            <option value="tl" >Top Left</option> \
                                            <option value="br" >Bottom Right</option> \
                                            <option value="bl" >Bottom Left</option> \
                                        </select> \
                                    </div>\
                                </div>\
                            </div> \
                            <div id="logo_picker" class="form-group" hidden> \
                                <label for="logo_pos" class="col-form-label"><b>Select Extra Logo</b></label> \
                                <select name="logo" hidden></select> \
                                <div id="logo_preview"></div>\
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

    // Default (or saved) Parameters
    $('input[name=extra_text]').val($('input[name=def_extra_text]').val());
    $('select[name=fps]').val($('input[name=def_fps]').val());
    $('select[name=dim]').val($('input[name=def_dim]').val());

  
    $('select[name=wat_pos]').val($('input[name=def_wat_pos]').val());
    $('select[name=text_pos]').val($('input[name=def_text_pos]').val());

   
    //Start datepicker
    load_date_pickers();

    // Avoid Same Location
    avoid_same_location();

    // If no custom logos...
    if($.trim($('input[name=logos]').val())=='') {
        $('select[name=extra_logo_yn]').attr('disabled','disabled');
    } else {
        //UI for custom logo
        add_custom_logo();
    }
   
    if($.trim($('input[name=def_extra_logo]').val())!=='') {
        $('select[name=extra_logo_yn]').val('y');
        $('select[name=extra_logo_yn]').trigger('change');
    } else {
       $('select[name=extra_logo_yn]').val('n');
    }
    


    // Generate
    $('#generate_timelapse').click(function() { 
        var cmd_data =  $("#timelapse_full_form").serializeObject(); //getFormData($("#timelapse_full_form"));
        cmd_data.cmd = "generate_timelapse";

        // AT LEAST ONE CAM NEEDS TO BE SELECTED
        if(typeof cmd_data['sel_cam[]'] == 'undefined') {
            bootbox.alert({
                message: "Please, select at least one camera",
                className: 'rubberBand animated error',
                centerVertical: true
            });
            
        } else {
            $('#full_timelapse_modal').modal('hide');
            loading({text: "Creating Video", overlay: true});
            
            $.ajax({ 
                url:  "/pycgi/webUI.py",
                data: cmd_data,
                success: function(data) {
                    var json_resp = $.parseJSON(data); 
                    bootbox.alert({
                        message: json_resp.msg + "<br/>This page will now reload.",
                        className: 'rubberBand animated',
                        centerVertical: true,
                        callback: function () {
                            location.reload();
                        }
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
        }

        
    });
}

$(function() {
    $('#create_timelapse').click(function() {
        add_timelapse_full_modal();    
    });
})