function meteor_is_deleted(id) {
      var $div = $('#'+id);
      $div.css('opacity',.5).removeClass('norm meteor reduced').addClass('del').find('.btn-toolbar').remove().end().find('a').removeAttr('href').removeAttr('title').attr('title','DELETED').unbind('mouseover').unbind('mouseout').end().find(".custom-checkbox").remove();                  
      $div.find('.overlay_loader').remove(); 
      $div.removeClass('selected');
      update_selected_counter();
}


function reject_meteor(id) {
      loading({text:"Deleting", container:$("#"+id), overlay:true});
      $.ajax({ 
            url:  "/api/delete_meteor/" + id + "/",
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

      console.log(array_of_jsid) 
      dlist = ""
      for (i = 0; i<=array_of_jsid.length-1; i++) 
      {
         dlist = dlist + array_of_jsid[i] + ";"
      }
    
      $.ajax({ 
            type:"POST",
            url:  "/api/delete_meteors/",
            data: {detections: dlist},
            success: function(data) {
                  
                  // TODO!!!!
                  // meteor_is_deleted(id);
                  // Debug
                  console.log(data);
                 
                  $.each(ids, function(i,v){
                        //console.log("IS DELETED " + v);
                        //console.log("I ", i);
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
