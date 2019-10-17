function update_url_param(url,param,value) {
   var url = new URL(url);
   var query_string = url.search;
   var search_params = new URLSearchParams(query_string); 

   // new value  
   search_params.set(param, value);

   // change the search property of the main url
   url.search = search_params.toString();

   // the new url string
   var new_url = url.toString();

   return new_url;
}


$(function() {
   $('#rpp').change(function() {
      window.location =  update_url_param(window.location.href ,'meteor_per_page',$('#rpp').val());
    });
})




