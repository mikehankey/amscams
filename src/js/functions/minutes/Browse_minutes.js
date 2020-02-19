$(function() {
   $('select[name=meteor_o]').on("change", function (e) {
      // Replace in cur URL and reload
      var cur_params = getQueryParameters(); 
      var param_to_update = $(this).attr('data-url-param');
      var v = $(this).val();
      cur_params[param_to_update]= v;
      setQueryParameters(cur_params[param_to_update]);
   })
})
       