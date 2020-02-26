/********** UI ***********************************************************************/
function setup_confirm_buttons() {
   $('.conf').each(function() {
      var $t = $(this); 
      $t.unbind('click').click(function() {   
         var $prevproc = $t.closest('.prevproc');

         if(!$prevproc.hasClass('done')) {
            $prevproc.removeClass('toDel');
            if($prevproc.hasClass('toConf')) {
               $t.addClass('on');
               $prevproc.removeClass('toConf');
            } else {
               $t.removeClass('on');
               $prevproc.addClass('toConf');
            }
         }

         
         check_bottom_action();


      });
   })

   // Conf ALL
   $('#conf_all').unbind('click').click(function() {
      $('.prevproc').each(function() {
         if(!$(this).hasClass('arc') && !$(this).hasClass('done')) {
            $(this).removeClass('toDel').addClass('toConf');
         }
      });
      check_bottom_action();
   })

   // Cancel All
   $('#cancel_all').unbind('click').click(function() {
      $('.prevproc').each(function(i,v){
         if(!$(this).hasClass('done') {
            $(this).removeClass('toDel').removeClass('toConf');
         }
      });
      check_bottom_action();
   })
}