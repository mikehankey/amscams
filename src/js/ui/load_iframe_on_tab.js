$('a.load-frames-on-active').on('shown.bs.tab', function(event){
   console.log($(event.target).text());
 });