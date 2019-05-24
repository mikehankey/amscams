$(function() {

    $('.del_row').click(function() {
        alert("WHAT")
        var  $row = $(this).closest('tr');
        var  id = $row.attr('id');
        var  $row = $(this).closest('table');
        var  id = $row.attr('id');
        $row.fadeOut(150, function() {$row.remove();})
    

         ajax_url = "/pycgi/webUI.py?cmd=del_frame&meteor_json_file=" + meteor_json_file + "&fn=" + id
         fr_id = "fr_row" + id
         //document.getElementById(fr_id).remove()
         console.log(ajax_url)
         //$.get(ajax_url, function(data) {
         //   $(".result").html(data);
         //   var json_resp = $.parseJSON(data);
         //   alert(json_resp['msg'])
         //});
      }
    
    })

})
