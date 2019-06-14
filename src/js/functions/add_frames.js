function add_reduc_row(data) {
    /*
        msg: "new frame added."
        newframe:
        az: 358.1230279283592
        b_10: NaN
        cnt_thumb: "/mnt/ams2/meteors/2019_06_13/2019_06_13_07_29_25_000_010033-trim1026-frm53.png"
        dec: 65.48315690419676
        el: 8.918430871796353
        est_x: 598
        est_y: 870
        fn: "53"
        frame_time: "2019-06-13 07:30:08.160"
        h: 5
        hd_x: 598
        hd_y: 864
        len_from_last: 6.324555320336759
        max_px: 0
        ra: 87.03382179634303
        w: 5
        x1: 573
        x2: 623
        y1: 839
        y2: 889
    */
    if(data.msg=='new frame added.') {
        var new_frame_id = parseInt(data.newframe.fn);

        // Try to find the row after first 
        var $tr_after = $('tr#'+ (new_frame_id-1));

        // If it doesn't exist
        if($tr_before.length==0) {
            // Add on first position
            $tr_before = $('#reduc-tab table tbody tr')[0];
        }

        var _time = data.newframe.frame_time;
        _time = _time.split(' ');
        _time = _time[1];

        // Build new row
        var row = "<tr id='fr_' "+ new_frame_id +" data-org-x='"+hd_x+"' data-org-y='"+hd_y+"'>";
        row += '<td><img alt="Thumb #'+new_frame_id+'" src="'+cnt_thumb+'" width="50" height="50" class="img-fluid select_meteor">';
        row += '<td>' + new_frame_id + '</td>';
        row += '<td>' + _time + '</td>'; 
        row += '<td>' + new_frame.ra.toFixed(3) + "&deg;/" + new_frame.dec.toFixed(3) + '&deg</td>';              
        row += '<td>' + new_frame.az.toFixed(3) + "&deg;/" + new_frame.el.toFixed(3) + '&deg</td>';               
        row += '<td>' + hd_x + "/" + hd_y + '</td>';              
        row += '<td>' + w + "/" + h + '</td>';            
        row += '<td>' + max_px + '</td>';      
        row += '<td>' + max_px + '</td>';      
        row += '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';
        row += '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>';

        $(row).insertBefore($tr_after);


            // Reload all actions on reduct table!!!

    }

    loading_done();
}

function add_a_frame(cur_fn) {
    loading({text: "Generating Frame #"+ cur_fn});
 
    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fn: cur_fn
    };

    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data, 
        success: function(data) { 
            
            add_reduc_row(data);
            
            bootbox.alert({
                message: "FRAME CREATED " + data,
                className: 'rubberBand animated',
                centerVertical: true 
            });
            
        }, 
        error:function() {
            loading_done();

            bootbox.alert({
                message: "The process returned an error",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
}

function setup_add_frames() {
    $('.add_f').click(function() {
        add_a_frame($(this).attr('data-rel'));
    }); 
}

 
