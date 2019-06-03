function reject_meteor(id) {
      loading({text:"Deleting"});
      $.ajax({ 
            url:  "webUI.py?cmd=override_detect",
            data: {jsid: id},
            success: function(data) {
                  loading_done();
                  $('#'+id).css('opacity',.5).removeClass('norm meteor reduced').addClass('del').find('.btn-toolbar').remove().end().find('a').removeAttr('src').removeAttr('title').attr('title','DELETED').unbind('mouseover').unbind('mouseout');                  
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