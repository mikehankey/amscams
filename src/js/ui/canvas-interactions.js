// Remove or add a star to user_stars
function update_user_stars() {
    /*
  var canvas_cnt = 0, diff;
  var canvas_stars = canvas.getObjects('circle');
  var init_start_cnt = parseInt($('#str_cnt').text());

    // Count the stars on the canvas
    $.each(canvas_stars, function(i,v) {
        if (v.get('type') == "circle" && v.get('radius') == 5) {
          canvas_cnt=canvas_cnt+1;
        }
    }); 

    diff = init_start_cnt - canvas_cnt;



    // Compare to total stars 
    if(canvas_cnt>parseInt($('#str_cnt').text())) {
      $('.star_counter_holder').css('visibility','visible');
      $('#update_stars').removeAttr('disabled').removeClass('disabled');
      $('#star_counter').val(canvas_cnt-$('#str_cnt').text());
    } else {
      $('.star_counter_holder').css('visibility','hidden');
      $('#update_stars').attr('disabled','disabled').addClass('disabled'); 
    }
    */
}
 


// All interactions with the canvas are defined below


if ($('canvas#c').length!=0) {
//&& (document.readyState === "complete")) {

  // Defined #c canvas
  var canvas = new fabric.Canvas('c', {
    hoverCursor: 'default',
    selection: true
  });

  var out_timer, in_timer;

  const render = canvas.renderAll.bind(canvas);

  // Loading Animation
  loading({'text':'Loading Media...','overlay':true});

  // Zoom
  function canvas_interactions() {

    var w_preview_dim = $('#canvas_zoom').innerWidth()/2;
    var h_preview_dim = $('#canvas_zoom').innerHeight()/2;
    var h_canvas_w = $('#c').innerWidth()/2;
    var h_canvas_h = $('#c').innerHeight()/2;
    
    var xRatio =  w_preview_dim / h_canvas_w;
    var yRatio =  h_preview_dim / h_canvas_h;
    
    var zoom = 4;

    $('#canvas_zoom').css({'background':'url('+hd_stack_file+') no-repeat 50% 50% #000','background-size': h_canvas_w*zoom + 'px ' + h_canvas_h*zoom + 'px' })
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

      // Hide grid on click
      if($('#c').hasClass('grid')) $('#show_grid').click();
    
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
        selectable: false,
        type: 'star_circle'
      });
    
      var objFound = false
      var clickPoint = new fabric.Point(x_val,y_val);
      var objects = canvas.getObjects('circle')
      
      for (let i in objects) {
        if (!objFound && objects[i].containsPoint(clickPoint)) {
            objFound = true
            canvas.remove(objects[i]);
          }
      }
      
      if (objFound == false) {
        canvas.add(circle); 
      }
     

    });
    
  }
    


  canvas.setBackgroundImage(
    my_image, function() {
      // Set Image 
      render();    
      
      // Show Grid if grid_by_default is set to true
      if(grid_by_default) $('#show_grid').click();

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
