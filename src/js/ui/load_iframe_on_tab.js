// Load the iframes on the tabd only when active
$('a.load-frames-on-active').on('shown.bs.tab', function(event){
   $($(this).href).find('iframe').each(function() {
      $(this).attr('data-src','src');
   });
 });