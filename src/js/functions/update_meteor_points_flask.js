function update_meteor_points(mfd) {
   rad = 5
   // Create Colors
   var rainbow = new Rainbow();
   rainbow.setNumberRange(0, 255);
   var all_colors = [];
   var total = mfd.length;
   var step = parseInt(255/total);
   for (var i = 0; i <= 255; i = i + step) {
       all_colors.push('#'+rainbow.colourAt(i));
   }


   for (i=0; i < mfd.length; i++) {
      [date, fn, x,y, w,h, int, ra,dec,az,el] = mfd[i]
      // Add Rectangle on canvas
      img_id = "#img_" + fn.toString()
      $(img_id).css('border-color',all_colors[i]);
      canvas.add(new fabric.Rect({
            fill: 'rgba(0,0,0,0)',
            strokeWidth: 1,
            stroke: all_colors[i], //'rgba(230,100,200,.5)',
            left:  (x/2)-rad,
            top:   (y/2)-rad,
            width: 10,
            height: 10 ,
            selectable: false,
            type: 'reduc_rect',
            id: 'fr_' + fn 
      }));
   }
}
