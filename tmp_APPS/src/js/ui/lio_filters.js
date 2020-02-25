$(function() {
   $('#lio_filters button').click(function() {
      var id = $(this).attr('id');
      
      $('.prevproc').hide();

      if(id=='lio_btn_all') {
         $('.prevproc').show();
      } else if(id=='lio_btn_pnd') {
         $('.prevproc.pending').show();
      } else if(id=='lio_btn_arc') {
         $('.prevproc.arc').show();
      }
   
   
   })
})
