function add_frame(cmd_data, fn) {
    loading({text: "Generating Frame "+ i +"/" + total,overlay:true});
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        fn: fn,
        async: false,
        success: function(data) {
            console.log(data);
            loading_done();
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
   
    for(var i=min_fn; i<=max_fn; i++) {
       
        add_frame(cmd_data,i);
       
    }

    loading_done();
}


add_frames();




