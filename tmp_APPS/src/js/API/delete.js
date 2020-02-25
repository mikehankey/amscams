/********** UI ***********************************************************************/
function setup_delete_buttons() { 
   $('.del').each(function() {
      var $t = $(this); 
      $t.unbind('click').click(function() {   
         $t.closest('.prevproc').removeClass('toConf');
         if($t.closest('.prevproc').hasClass('toDel')) {
            $t.addClass('on');
            $t.closest('.prevproc').removeClass('toDel');
         } else {
            $t.removeClass('on');
            $t.closest('.prevproc').addClass('toDel');
         }
         check_bottom_action();
      });
   })
}

/********** API **************************************
function delete_detec(detect_id) {
 
   $.ajax({ 
      url:   API_URL ,
      data: {'function':'delete',  'tok':TOK, 'detect': detect_id, 'st': STATION, 'user':USR}, 
      format: 'json',
      success: function(data) { 
         data = jQuery.parseJSON(data); 
         if(typeof data.error !== 'undefined') {
            // WRONG!
            bootbox.alert({
               message: data.error,
               className: 'rubberBand animated error',
               centerVertical: true 
            });
         } else {
            $('#'+detect_id).addClass('deleted');
         } 
      }, 
      error:function() { 
         bootbox.alert({
            message: "Impossible to reach the API. Please, try again later or refresh the page and log back in",
            className: 'rubberBand animated error',
            centerVertical: true 
         });
      }
   });
}*********************************/