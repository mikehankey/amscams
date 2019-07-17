// Update counter
function update_selected_counter() {
    $('#sel-ctn').text($('.preview.selected').length);
}


$(function() {

    // Select one
    $('.sel-box input[type=checkbox]').change(function() {
        var $t = $(this), f = $t.attr('id'), id = f.substr(5,f.length);
        if($t.is(':checked')) {
            $('#'+id).addClass('selected');
        } else {
            $('#'+id).removeClass('selected');
        }
         update_selected_counter();
     });
    
     // Select All
     $('#sel-all').click(function() {
        $('.sel-box input[type=checkbox]').click();
        update_selected_counter();
     })

     // Delete All
     $('#del-all').click(function() {
         // Get all id
     
         var detections = [];
         var ids = [];
         jQuery.each($('.preview.selected'), function( i, val ) { 
                var lnk = $(val).find('a').attr('href');
                var params = [];
                lnk.replace(/([^=]*)=([^&]*)&*/g, function (_, key, value) {
                    params[key] = value;
                });
                detections.push(params['video_file']);
                ids.push($(val).attr('id'));
            }
         );
        reject_multiple_meteor(detections, ids);

         
     })
})
