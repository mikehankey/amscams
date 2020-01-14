//

$(function() {
   $('.chg_arc_opts').click(function() {
      var rel = $(this).attr('data-rel');
      if(rel=='y') {
         Cookies.set('video_prev', 1, { expires: 99999, path: '/' });
      } else {
         Cookies.set('video_prev', 0, { expires: 99999, path: '/' });
      }

      // We reload the page
      window.location.reload();
   })
})