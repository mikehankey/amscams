$(function() {
   $('select[name=meteor_o]').on("dp.change", function (e) {
      // Replace in cur URL and reload
      var cur_params = getQueryParameters(); 
      var param_to_update = $t.attr('data-url-param');
      setQueryParameters(cur_params[param_to_update]);
   })
})
       