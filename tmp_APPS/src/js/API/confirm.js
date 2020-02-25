/********** UI ***********************************************************************/
function setup_confirm_buttons() {
   $('.conf').each(function() {
      var $t = $(this); 
      $t.unbind('click').click(function() {   
         $t.closest('.prevproc').removeClass('toDel');
         if($t.closest('.prevproc').hasClass('toConf')) {
            $t.addClass('on');
            $t.closest('.prevproc').removeClass('toConf');
         } else {
            $t.removeClass('on');
            $t.closest('.prevproc').addClass('toConf');
         }
         check_bottom_action();
      });
   })

   // Conf ALL
   $('#conf_all').unbind('click').click(function() {
      $('.prevproc').each(function() {
         if(!$(this).hasClass('arc')) {
            $(this).removeClass('toDel').addClass('toConf');
         }
      });
      check_bottom_action();
   })

   // Cancel All
   $('#cancel_all').unbind('click').click(function() {
      $('.prevproc').removeClass('toDel').removeClass('toConf');
      check_bottom_action();
   })
}