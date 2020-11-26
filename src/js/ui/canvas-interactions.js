var stars_added   = 0;
var stars_removed = 0;

var HD_w = 1920;
var HD_h = 1080;


// Remove or add a star to user_stars
function update_user_stars() {

    if(stars_added!==0 || stars_removed!==0) {
     
      if(stars_added !== 0 ) {
          $('#star_counter').css('visibility','visible');

          if(stars_added>1) {
           $('#star_counter').text(stars_added + ' stars added');
          } else {
           $('#star_counter').text(stars_added + ' star added');
          }

          if(stars_removed != 0) {
            if(stars_removed>1) {
              $('#star_counter').text($('#star_counter').text() + ' and ' + stars_removed + ' stars removed');
            } else {
              $('#star_counter').text($('#star_counter').text() + ' and ' + stars_removed + ' star removed');
            }
            
          }
      } else if(stars_removed!==0) {
          $('#star_counter').css('visibility','visible');
          if(stars_removed>1) {
            $('#star_counter').text(stars_removed + ' stars removed');
          } else {
            $('#star_counter').text(stars_removed + ' star removed');
          }
      }

        $(window).unbind('beforeunload').bind('beforeunload', function(){
          return 'You have unsave updates on the star list. Are you sure you want to leave?';
        });
 
    } else {
        $('#star_counter').css('visibility','hidden').text('');
        $(window).unbind('beforeunload');
    }
   
 
}
 
 
// All interactions with the canvas are defined below


if ($('canvas#c').length!=0) { 

  // Defined #c canvas
  var canvas = new fabric.Canvas('c', {
    hoverCursor: 'default',
    selection: true 
  });

  var out_timer, in_timer;
  const render = canvas.renderAll.bind(canvas);

  // Loading Animation
  //loading({'text':'Loading Meteor Media...','overlay':true});

  // Zoom
  function canvas_interactions() {

    var w_preview_dim = $('#canvas_zoom').innerWidth()/2;
    var h_preview_dim = $('#canvas_zoom').innerHeight()/2;
    var h_canvas_w = $('#c').innerWidth()/2;
    var h_canvas_h = $('#c').innerHeight()/2;
    
    var xRatio =  w_preview_dim / h_canvas_w;
    var yRatio =  h_preview_dim / h_canvas_h;
    
    var zoom = 4;

    // We compute the W_factor & H_factor
    // to pass the equivalent of HD x,y on the RADEC_MODE
    var wRatio = HD_w/$('#c').innerWidth();
    var hRatio = HD_h/$('#c').innerWidth();

    $('#canvas_zoom').css({'background':'url('+my_image +') no-repeat 50% 50% #000','background-size': h_canvas_w*zoom + 'px ' + h_canvas_h*zoom + 'px' })
    $('.canvas_zoom_holder').css({'width':w_preview_dim*2, 'height':h_preview_dim*2,'position':'absolute'});


    // Hide the option by default
    $('.canvas_zoom_holder').slideUp(250, function() { $(this).css('visibility','visible')}); 
    

    // Hide/Show zoom when necessary
    $('.canvas-container canvas').mouseenter(function(){ 
      out_timer = setTimeout(function() { $('.canvas_zoom_holder').slideDown(300);},350);
    }).mouseleave(function() { 
      clearTimeout(out_timer);
      out_timer = setTimeout(function() {
        $('.canvas_zoom_holder').slideUp(300); 
        $('#canvas_zoom').css('background-position','50% 50%');
      }, 350); 
    }); 
 
    canvas.on('mouse:move', function(e) { 
        var pointer = canvas.getPointer(event.e);
        var $zoom   = $('#canvas_zoom');
        var x_val = pointer.x | 0;
        var y_val = pointer.y | 0;
  
        x_val = x_val*zoom/2-w_preview_dim;
        y_val = y_val*zoom/2-h_preview_dim;
      
        if(x_val<0) {
          if(y_val<0) {
            $zoom.css('background-position',Math.abs(x_val)  + 'px ' + Math.abs(y_val) + 'px');
          } else {
            $zoom.css('background-position', Math.abs(x_val)  + 'px -' + y_val  + 'px');
          }
        } else if(y_val<0) {
            $zoom.css('background-position','-' +  x_val  + 'px ' + Math.abs(y_val)  + 'px');
        } else {
          
            $zoom.css('background-position', '-'+x_val  + 'px -' + y_val  + 'px');
        }
        //$('#canvas_pointer_info').text(x_val +', '+ y_val); 
        $('#canvas_pointer_info').text(Math.round(pointer.x) +', '+ Math.round(pointer.y)); 
    }); 
    
    canvas.on('mouse:down', function(e) {
      // Remove zoom
      if($('#c').hasClass('r-zoomed')) {
         $('#c').removeClass('r-zoomed').removeAttr('style'); 
         return false;
      }  
      
      // Hide grid on click
      if($('#c').hasClass('grid')) $('#show_grid').click();
     
      // Not in RADEC_MODE: it means we select stars on the canvas
      if(RADEC_MODE==false) {
         // Make the update star button blinked
        make_it_blink($('#update_stars'));

        var pointer = canvas.getPointer(event.e);
        x_val = pointer.x | 0;
        y_val = pointer.y | 0;
  
        var circle = new fabric.Circle({
          radius: 5, 
          fill: 'rgba(0,0,0,0)', 
          strokeWidth: 1, 
          stroke: 'rgba(100,200,200,.85)', 
          left: x_val-5, 
          top: y_val-5,
          selectable: false 
        }); 

        var objFound = false;
        var grpFound = false;
        var clickPoint = new fabric.Point(x_val,y_val);
        var objects = canvas.getObjects('circle');
        var id;
         
        // Remove an existing star
        for (let i in objects) {
          if (!objFound && objects[i].containsPoint(clickPoint)) {
              objFound = true;
              id = objects[i].gp_id;
              canvas.remove(objects[i]);
            }
        }

        // Remove all the related object +, name, square if
        // it's a start from the catalog
        if(objFound && $.trim(id)!=='') { 
          objects = canvas.getObjects();
          for (let i in objects) {
                if(objects[i].gp_id== id) { 
                  canvas.remove(objects[i]);
                  grpFound = true;
                }
          }
        }  
  

        if(objFound && grpFound) {
          // An existing star has been removed 
          stars_removed += 1;
        } else if( objFound && !grpFound) {
          stars_added -=  1;
        } else if(!objFound && !grpFound) {
          stars_added += 1;
        }
    
        
        if (objFound == false) {
          canvas.add(circle); 
        }
        
        update_user_stars();
      } else {

         // Here we just point at the canvas to get RA/Dec
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
   
         var marker = new fabric.Circle({
           radius: 5, 
           fill: 'rgba(0,0,0,0.3)', 
           strokeWidth: 1, 
           stroke: 'rgba(255,0,0,1)', 
           left: x_val-5, 
           top: y_val-5,
           selectable: false,
           type: "getradec"
         }); 

         canvas.add(marker); 

         // Add the object info in rad_dec_object
         new_rad_dec_obj = {x_org: x_val, y_org: y_val, x_HD: wRatio*x_val, y_HD: hRatio*y_val};
         rad_dec_object.push(new_rad_dec_obj);
         // Add info to the panel on the page
         add_radec_info(new_rad_dec_obj)

      }
        

        
      
        
    });
    
  }
    


  canvas.setBackgroundImage(
    my_image, function() {
      // Set Image 
      render();    
      
      // Show Grid if grid_by_default is set to true
      if(typeof grid_by_default !=="undefined" && grid_by_default) $('#show_grid').click();

      // Setup Interactions
      canvas_interactions();

      // End Loading Animation
      loading_done(); 
      
 
    },
    {
      width: canvas.width,
      height: canvas.height, 
      originX: 'left',
      originY: 'top'
  });
 
  // Add Stars 
  var user_stars = [];

  if(typeof stars !== 'undefined') {
   for (let s in stars) {
      cx = stars[s][0] - 11;
      cy = stars[s][1] - 11;

      var circle = new fabric.Circle({
          radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
          selectable: false
      });
      canvas.add(circle);
   }  
  }
 
}
