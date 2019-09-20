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

// Build draggable panel for RAD/DEC
function build_radecpanel() {
   $('#main_container').prepend($('<div id="select_f_tools" class="ui-draggable" style="width: 300px;height: 300px;overflow:auto;color:#fff;background:#000;padding: 0.2rem .3rem;font-family: monospace;">\
      <div class="drag-h d-flex justify-content-between pt-1 ui-draggable-handle">\
         <small>RA/Dec Mode</small>\
      </div>\
      <div class="p-1">\
      <textarea id="radec_info" style="width: 300px; height: 300px; overflow:auto; color:#fff; background:#000"></textarea>\
      </div></div>'));

      // Make it draggable
      $( "#select_f_tools" ).draggable(
         {   containment: $('body'),
             drag:function(e,u) {   
                 var top = u.position.top;
                 var left = u.position.left;
             }
     });
}

// Add and info to the draggable panel for RA/DEC
function add_radec_info(info) {
   $('#radec_info').val($('#radec_info').val()+"\nx:"+info['x_org']+" ,y:"+info['y_org']+" - HD x:"+ info['x_HD'] + ", y:" + info['y_HD']);
}


$('#radec_mode').click(function() {
   RADEC_MODE = !RADEC_MODE;
   
   console.log("RADEC_MODE ", RADEC_MODE );

   if(RADEC_MODE) {
      // We hide the stars
      remove_stars_info_from_canvas();

      // We add the radec panel
      build_radecpanel();

   } else {
      // We put back the stars
      add_stars_info_on_canvas();

      // Remove the radec info from canvas
      remove_radec_info_from_canvas();

      // We empty rad_dec_object
      rad_dec_object = [];
   }
})