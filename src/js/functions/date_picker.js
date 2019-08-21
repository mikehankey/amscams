function getQueryParameters() {
    var queryString = location.search.slice(1),
        params = [];
  
    queryString.replace(/([^=]*)=([^&]*)&*/g, function (_, key, value) {
      params[key] = value;
    });
  
    return params;
  }

function setQueryParameters(params) {
    var query = [],
        key, value;
  
    for(key in params) {
      if(!params.hasOwnProperty(key)) continue;
      value = params[key];
      query.push(key + "=" + value);
    }
    
    location.search = query.join("&");
}


function load_date_pickers() {
    $('.datepicker').each(function() {
        var $t = $(this);
        $t.datetimepicker({format: $t.attr('data-display-format')});
 
        if($t.attr('data-action')=='reload') {

            $t.on("dp.change", function (e) {
                
                // Convert date
                var new_date = e.date.format($t.attr('data-send-format'));
                 
                // Replace in cur URL and reload
                var cur_params = getQueryParameters();
                // WARNING limit_day is hardcoded here
                var param_to_update = $t.attr('data-url-param');
                 
                if(cur_params[param_to_update] != new_date) {
                    cur_params[param_to_update] = new_date;
                    setQueryParameters(cur_params);
                }
                 

            });
        }
    });
}

$(function() {
    load_date_pickers()
})