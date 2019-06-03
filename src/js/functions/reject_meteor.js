function reject_meteor(id) {
      loading({text:"Deleting"});
      $.ajax({ 
            url:  "webUI.py?cmd=override_detect",
            data: {jsid: id},
            success: function(data) {
                  loading_done();
                  $('#id').fadeOut(200, function() {
                        $(this).remove();
                  });
 
                  // Debug
                  console.log(data);
            }, 
            error: function() {
                  alert('Impossible to reject. Please try again later')
                  loading_done();
            }
      });
}
  

$(function() {
      $('.delete_meteor_gallery').click(function() {
            reject_meteor($(this).attr('data-meteor'));
      })
})