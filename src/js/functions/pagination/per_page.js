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

      var rpp = $('#rpp').val();

      // Add the cookie (works only for the archive page)
      Cookies.set('archive_rpp', rpp, { expires: 99999, path: '/' });

      // Change Meteor Per page
      new_url = update_url_param(window.location.href ,'meteor_per_page',rpp);

      // Back to page = 1 (so we dont have issues if the number of page is too mall)
      window.location =  update_url_param(new_url ,'p',1);
    });
})




