function meteor_is_deleted(id) {
      $('#'+id).css('opacity',.5).removeClass('norm meteor reduced').addClass('del').find('.btn-toolbar').remove().end().find('a').removeAttr('href').removeAttr('title').attr('title','DELETED').unbind('mouseover').unbind('mouseout').end().find(".custom-checkbox").remove();                  

}


function reject_meteor(id) {
      loading({text:"Deleting", container:$("#"+id)});
      $.ajax({ 
            url:  "webUI.py?cmd=override_detect",
            data: {jsid: id},
            success: function(data) {
                  loading_done();
                  meteor_is_deleted(id);
                  // Debug
                  //console.log(data);
            }, 
            error: function() {
                  alert('Impossible to reject. Please, reload the page and try again later.')
                  loading_done();
            }
      });
}
  

$(function() {
      $('.delete_meteor_gallery').click(function() {
            reject_meteor($(this).attr('data-meteor'));
      })
})