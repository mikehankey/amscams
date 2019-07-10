function meteor_is_deleted(id) {
      $('#'+id).css('opacity',.5).removeClass('norm meteor reduced').addClass('del').find('.btn-toolbar').remove().end().find('a').removeAttr('href').removeAttr('title').attr('title','DELETED').unbind('mouseover').unbind('mouseout').end().find(".custom-checkbox").remove();                  
      $('#'+id).find('.overlay_loader').remove(); 
      update_selected_counter();
}


function reject_meteor(id) {
      loading({text:"Deleting", container:$("#"+id), overlay:true});
      $.ajax({ 
            url:  "webUI.py?cmd=override_detect",
            data: {jsid: id},
            success: function(data) {
                  meteor_is_deleted(id); 
            }, 
            error: function() {
                  alert('Impossible to reject. Please, reload the page and try again later.')
                  loading_done();
            }
      });
}
 


function reject_multiple_meteor(array_of_jsid, ids) {
      // Deleting
      $.each(ids, function(i,v){ 
            loading({text:"Deleting", container:$("#"+v), overlay:true, standalone:true});
      });

      //console.log("array_of_jsid ", array_of_jsid)

      $.ajax({ 
            url:  "webUI.py?cmd=delete_multiple_detection",
            data: {detections: array_of_jsid},
            success: function(data) {
                  
                  // TODO!!!!
                  // meteor_is_deleted(id);
                  // Debug
                  //console.log(data);
            
                  $.each(ids, function(i,v){
                        console.log("IS DELETED " + v);
                        console.log("I ", i);
                        meteor_is_deleted(v); 
                  });
                  
                 
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