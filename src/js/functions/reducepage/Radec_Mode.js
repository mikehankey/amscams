var RADEC_MODE = false; // Shared with canvas-interactions

var star_info_object = [];  // Store the canvas objects related to the stars
var rad_dec_object = [];    // Store the canvas objects related to the radec_mode

// Hide object of a certain type from the canvas
function hide_type_from_canvas(type) {
   var objects = canvas.getObjects()
   $.each(objects,function(i,v){
       if(v.type==type) {
         star_info_object.push(objects[i]);
         canvas.remove(objects[i]);
       }
   });
}

// Remove All stars info from canvas
function remove_stars_info_from_canvas() {
   hide_type_from_canvas('star_info');
}

// Put All Starts info on canvas
function add_stars_info_on_canvas() { 
   $.each(star_info_object,function(i,v){
      canvas.add(star_info_object[i]);
   });
   star_info_object = [];
}


// Remove All getradec markers from canvas
function remove_radec_info_from_canvas() {
   hide_type_from_canvas('getradec'); 
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

      // Remove the radec info from canvas
      remove_radec_info_from_canvas();

      // We empty rad_dec_object
      rad_dec_object = [];
   }
})