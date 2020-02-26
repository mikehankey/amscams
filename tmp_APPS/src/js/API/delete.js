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

   $('#del_all').unbind('click').click(function() {
      $('.prevproc').each(function() {
         if(!$(this).hasClass('arc')) {
            $(this).removeClass('toConf').addClass('toDel');
         }
      }); 
      check_bottom_action();
   });
 
   
}

 