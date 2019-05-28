 $(function() {

    // Delete Frame
    $('.delete_frame').click(function() {
        var  $row = $(this).closest('tr');
        var  id = $row.attr('id');
 
        $row.fadeOut(150, function() {$row.remove();})
 
        $.ajax({ 
            url:  "/pycgi/webUI.py?cmd=del_frame&meteor_json_file=" + meteor_json_file + "&fn=" + fn,
            success: function(response) {
                 console.log($.parseJSON(response));
            } 
        });
      
    })

})

 