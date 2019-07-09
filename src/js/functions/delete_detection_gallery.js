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
     

         jQuery.each($('.preview.selected'), function( i, val ) { 
                var toSend = [];
                $.each(val,function() {
                    toSend.push($(val).attr('id'));
                })
                //console.log(toSend);
                //reject_meteor($(val).attr('id'));
            }
         );

         reject_multiple_meteor(toSend);

         
     })
})
