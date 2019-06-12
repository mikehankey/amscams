function add_frame(cmd_data,min_fn,max_fn,total) {

    var cur_fn = min_fn;

    loading({text: "Generating Frame "+ cur_fn +"/" + total,overlay:true});
    cmd_data.fn = cur_fn;
    
    console.log("DOING ", cmd_data);

    $.ajax({ 
        url:  "/pycgi/WebUI.py",
        data: cmd_data,
        async: false,
        success: function(data) {
            console.log(data);
            loading_done();
            
            if(cur_fn<max_fn) {
                cmd_data.fn = cur_fn+1;
                add_frame(cmd_data,cmd_data.fn,max_fn,total);
            }
            
        }, 
        error:function() {
            bootbox.alert({
                message: "The process returned an error",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
} 
 
function add_frames() {
    var all_frame_ids = [];

    // Get All Frame Ids
    $('#reduc-tab tbody tr').each(function() {
        var cur_frame_number = $(this).attr('id');
        cur_frame_number = cur_frame_number.split('_');
        all_frame_ids.push(parseInt(cur_frame_number[1]));
    });

    // Get max frame #
    var max_fn = Math.max.apply(Math, all_frame_ids);
    var min_fn = Math.min.apply(Math, all_frame_ids);
    var total  = max_fn-min_fn;

    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
    };
   
    add_frame(cmd_data,min_fn, max_fn,total);
    loading_done();
}
 


$(function() {
    $('#fix_frames').click(function() {
        add_frames();
    });
})

/********************************************** */



function add_a_frame(cur_fn) {
    loading({text: "Generating Frame #"+ cur_fn});

    
    var cmd_data = {
		cmd: 'add_frame',
        sd_video_file: sd_video_file, // Defined on the page
        fn: cur_fn
    };

    $.ajax({ 
        url:  "/pycgi/WebUI.py",
        data: cmd_data, 
        success: function(data) { 
            loading_done();
            
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

$(function() {
    $('.add_f').click(function() {
        add_a_frame($(this).attr('data-rel'));
    }); 
})