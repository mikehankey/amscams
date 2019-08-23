// Update counter
function update_selected_counter() {
    $('.sel-ctn').text($('.preview.selected').length);
}


$(function() {

    // Select one from checkbox
    $('.sel-box input[type=checkbox]').change(function() {
        var $t = $(this), f = $t.attr('id'), id = f.substr(5,f.length);
        if($t.is(':checked')) {
            $('#'+id).addClass('selected');
        } else {
            $('#'+id).removeClass('selected');
        }
         update_selected_counter();
     });


     // Select one from div
     $('.select-to').click(function(e) {
         if($(e.target).hasClass('select-to')) {
            console.log('IT IS SELECT-TO')
            e.stopImmediatePropagation();
            $(this).find('.sel-box input[type=checkbox]').click();
         }
     })
    
     // Select All
     $('#sel-all').click(function() {
        $('.sel-box input[type=checkbox]').click();
        update_selected_counter();
     })

     // Delete All
     $('.del-all').click(function() {
         // Get all id
     
         var detections = [];
         var ids = [];
         jQuery.each($('.preview.selected'), function( i, val ) { 
                detections.push($(val).find('.delete_meteor_gallery').attr('data-meteor'));
                ids.push($(val).attr('id'));
            }
         );
        reject_multiple_meteor(detections, ids);

         
     })
})
