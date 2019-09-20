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
   $('#main_container').prepend($('<div id="select_f_tools" class="ui-draggable" style="width: 388px;position:absolute;z-index:999; color:#fff;background:#000;padding: 0.2rem .3rem;font-family: monospace; left: -150px;  top: -10px;">\
      <div class="drag-h d-flex justify-content-between pt-1 ui-draggable-handle">\
         <small>RA/Dec Mode</small>\
      </div>\
      <div class="p-1">\
      <textarea id="radec_info" style="width: 370px; height: 300px; overflow:auto; color:#fff; background:#000"></textarea>\
      <button id="get_radec_info" class="btn btn-primary btn-sm d-block" style="margin: 0 auto;"><span class="icon-cogs"></span> Resolve RA/Dec</button>\
      </div></div>'));

      // Make it draggable
      $( "#select_f_tools" ).draggable(
         {   containment: $('body'),
             drag:function(e,u) {   
                 var top = u.position.top;
                 var left = u.position.left;
             }
     });
 
     // Click on resolve button 
     $('#get_radec_info').click(function() {
         loading({text: "Resolving...", overlay:true});

         $.ajax({ 
            url:  "/pycgi/webUI.py",
            data: {
                cmd: 'getRADEC',
                json_file: json_reduced,
                values: JSON.stringify(rad_dec_object)
            }, 
            success: function(data) {
               loading_done();
               data = JSON.parse(data); 

               // We hide all the radec_info form the canvas
               remove_radec_info_from_canvas();

               // Reset Panel
               $('#radec_info').val('');

               // We add back the stuff on the canvas
               $.each(data['res'], function(i,v){
                  canvas.add(new fabric.Circle({
                     radius: 5, 
                     fill: 'rgba(0,0,0,0.3)', 
                     strokeWidth: 1, 
                     stroke: 'rgba(0,0,255,1)', 
                     left: v['x_org']-5, 
                     top: v['y_org']-5,
                     selectable: false,
                     type: "getradec"
                  }));
                   
                   canvas.add(new fabric.Text(
                        "Az: " + v['az'].toFixed(3)  + "\nEl: " + v['el'].toFixed(3), {
                        fontFamily: 'Arial', 
                        fontSize: 12, 
                        top:  v['y_org'],
                        left:  v['x_org'] + 11,
                        fill:'rgba(255,255,255,.45)',
                        selectable: false,
                        gp_id: v[0],
                        type: 'getradec',
                     }));

                   // Add info to the Panel
                     add_radec_resolved_info(v);
               });

              

              
            }
         });
     })
}

// Add info to the draggable panel for RA/DEC
function add_radec_info(info) {
   var step = '\n';
   if($.trim($('#radec_info').val()) == '') {
      step = '';
   }
   $('#radec_info').val($('#radec_info').val()+ step + "x:"+info['x_org']+", y:"+info['y_org']+" - HD x:"+ info['x_HD'] + ", y:" + info['y_HD']);
}

// Add resolved info to the draggable panel for RA/DEC
function add_radec_resolved_info(info) {
   var step = '\n';
   if($.trim($('#radec_info').val()) == '') {
      step = '';
   }
   $('#radec_info').val($('#radec_info').val()+ step + "x:"+info['x_org']+", y:"+info['y_org']+"\n - Az:"+ info['az'].toFixed(4) + ", El:" + info['el'].toFixed(4)+"\n - RA:"+ info['ra'].toFixed(4) + ", Dec:" + info['dec'].toFixed(4));
}


$('#radec_mode').click(function() {
 
   if(typeof json_reduced  == "undefined") {
      loading_done();
      bootbox.alert({
          message: "JSON file is missing. A JSON files with calibration parameters is required (-reduced.json).<br/>",
          className: 'rubberBand animated error',
          centerVertical: true 
      });
   } else {
      RADEC_MODE = !RADEC_MODE;
    
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

         // We delete the panel
         $('#select_f_tools').remove();
      }
   }

   
})