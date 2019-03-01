var canvas = new fabric.Canvas('c', {
         hoverCursor: 'default',
         selection: true
      });
var user_stars = []
 for (let s in stars) {

              cx = stars[s][0] - 11
              cy = stars[s][1] - 11

              var circle = new fabric.Circle({
                 radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                 selectable: false
              });
              canvas.add(circle);

            } 


//canvas.setBackgroundImage(my_image, canvas.renderAll.bind(canvas));

canvas.on('mouse:move', function(e) {
   var pointer = canvas.getPointer(event.e);
   x_val = pointer.x | 0;
   y_val = pointer.y | 0;
   cx = 2
   cy = 2
   document.getElementById('info_panel').innerHTML = x_val.toString() + " , " + y_val.toString()
   myresult = document.getElementById('myresult')
   myresult.style.backgroundImage = "url('" + hd_stack_file + "')";
   myresult.style.backgroundPosition = "-" + ((x_val*cx)-25) + "px -" + ((y_val * cy)-25)  + "px"
});

canvas.on('mouse:down', function(e) {
   var pointer = canvas.getPointer(event.e);
   x_val = pointer.x | 0;
   y_val = pointer.y | 0;
   user_stars.push([x_val,y_val])

   var circle = new fabric.Circle({
   radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: x_val-5, top: y_val-5,
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


   document.getElementById('info_panel').innerHTML = "star added"
   document.getElementById('star_panel').innerHTML = "Total Stars: " + user_stars.length;
});

