if($('canvas#c').length!=0) {



// Defined #c canvas
var canvas = new fabric.Canvas('c', {
  hoverCursor: 'default',
  selection: true
});

const render = canvas.renderAll.bind(canvas);

// Loading Animation
loading(true);

function canvas_interactions() {

  var w_preview_dim = $('#canvas_zoom').innerWidth()/2;
  var h_preview_dim = $('#canvas_zoom').innerHeight()/2;
  var h_canvas_w = $('#c').innerWidth()/2;
  var h_canvas_h = $('#c').innerHeight()/2;
  
  var xRatio =  w_preview_dim / h_canvas_w;
  var yRatio =  h_preview_dim / h_canvas_h;
  

  $('#canvas_zoom').css({'background':'url('+hd_stack_file+') no-repeat 50% 50% #000'});
 // $('#canvas_zoom').css({'background-size': h_canvas_w*zoom + 'px ' + h_canvas_h*zoom + 'px' })
  // Hide the option by default
  $('.canvas_zoom_holder').slideUp(); 
 

  canvas.on('mouse:move', function(e) {
      var pointer = canvas.getPointer(event.e);
      var $zoom   = $('#canvas_zoom');
      var x_val = pointer.x | 0;
      var y_val = pointer.y | 0;
     
      //  x_val = Math.round(x_val-w_preview_dim); ///h_canvas_w*zoom*ratio;
      //y_val = Math.round(y_val-h_preview_dim);// /h_canvas_h*zoom*(1/ratio);

   //     console.log('X ', x_val, '  Y', y_val);

     

      x_val = x_val-w_preview_dim;
      y_val = y_val-h_preview_dim;
     // console.log('X ', x_val, '  Y', y_val);

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

    if($('#c').hasClass('grid')) $('#show_grid').click();
  
    var pointer = canvas.getPointer(event.e);
    x_val = pointer.x | 0;
    y_val = pointer.y | 0;
    user_stars.push([x_val,y_val])
  
    var circle = new fabric.Circle({
      radius: 5, 
      fill: 'rgba(0,0,0,0)', 
      strokeWidth: 1, 
      stroke: 'rgba(100,200,200,.85)', 
      left: x_val-5, 
      top: y_val-5,
      selectable: false
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
   
    $('#canvas_pointer_info').text('Star Added');
  });
   
}
  


canvas.setBackgroundImage(
  my_image, function() {
    // Set Image 
    render();    
    var grid_by_default = false 
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
