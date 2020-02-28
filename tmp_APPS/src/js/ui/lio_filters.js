$(function() {
   $('#lio_filters button').click(function(e) {
      e.stopImmediatePropagation();

      var id = $(this).attr('id');

      $('#lio_filters button').removeClass('active');
      $('.prevproc').hide();

      if(id=='lio_btn_all') {
         $('.prevproc').show();
      } else if(id=='lio_btn_pnd') {
         $('.prevproc.pending').show();
      } else if(id=='lio_btn_arc') {
         $('.prevproc.arc').show();
      }

      $('.btn#'+id).addClass('active'); 
   })

   $('#lio_sub_filters button').click(function(e) {
      e.stopImmediatePropagation();

      var id = $(this).attr('id');

      $('#lio_sub_filters button').removeClass('active');
      $('.prevproc').hide();

      if(id=='lio_sub_btn_all') {
         $('.prevproc').show();
      } else if(id=='lio_sub_btn_single') {
         $('.prevproc.single').show();
      } else if(id=='lio_sub_btn_multi') {
         $('.prevproc.multi').show();
      }

      $('.btn#'+id).addClass('active'); 
   })
})
