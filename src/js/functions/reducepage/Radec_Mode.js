var RADEC_MODE = false; // Shared with canvas-interactions

var star_info_object = [];


// Remove All stars info from canvas
function remove_stars_info_from_canvas() {
   var objects = canvas.getObjects()
   $.each(objects,function(i,v){
       if(v.type=='star_info') {
         star_info_object.push(objects[i]);
         canvas.remove(objects[i]);
       }
   });
}

// Put All Starts info on canvas
function add_stars_info_on_canvas() { 
   $.each(star_info_object,function(i,v){
      canvas.add(star_info_object[i]);
   });
   star_info_object = [];
}


$('#radec_mode').click(function() {
   RADEC_MODE = !RADEC_MODE;
   
   console.log("RADEC_MODE ", RADEC_MODE );

   if(RADEC_MODE) {
      // We hide the stars
      remove_stars_info_from_canvas();
   } else {
      // We put back the stars
      add_stars_info_on_canvas();
   }
})