$(function() {

    $('.delete_row').click(function() {
        var  $row = $(this).closest('tr');
        var  id = $row.attr('id');
        $row.fadeOut(150, function() {$row.remove();})
    
        alert('DO SOMETHING WITH THE ID ' + id);
    
    })

})