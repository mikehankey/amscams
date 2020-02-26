/********** UI ***********************************************************************/
function setup_delete_buttons() { 
   $('.del').each(function() {
      var $t = $(this); 
      $t.unbind('click').click(function() {   

         var prevproc =  $t.closest('.prevproc');
            if(!prevproc.hasClass('done')) {
               prevproc.removeClass('toConf');
            if(prevproc.hasClass('toDel')) {
               $t.addClass('on');
               prevproc.removeClass('toDel');
            } else {
               $t.removeClass('on');
               prevproc.addClass('toDel');
            }
         }
         
         check_bottom_action();
      });
   })

   $('#del_all').unbind('click').click(function() {
      $('.prevproc').each(function(){
         if(!$(this).hasClass('done') && !$(this).hasClass('arc'))) {
            $(this).removeClass('toConf').addClass('toDel');
         }
      });
 
      check_bottom_action();
   });
 
   
}

 