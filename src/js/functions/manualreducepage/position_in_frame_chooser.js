
var frames_done=[];  // Just for the frames done
var frames_jobs=[];  // All the info for the frames done

// Fix the height of the chooser
function fix_pifc_ui() {
   var fh = $('#footer').outerHeight();
 
   // It's too small...
   if($(window).outerHeight()-fh-$('#main_container').outerHeight() > 60) {
      while($(window).outerHeight()-fh-$('#main_container').outerHeight() > 60) {
         $('#cropped_frame_selector').height($('#cropped_frame_selector').height()+1)
      }

      // Keep Ratio
      $('#cropped_frame_selector').width($('#cropped_frame_selector').height()*w/h);

   }

   // Change Markers 
   $('#org_lh, #lh').css('width','100%');
   $('#org_lv, #lv').css('height','100%');

}


// Init actions
function setup_init_pos_choos_actions() {

   var selector_width = $('#cropped_frame_selector').outerWidth();
   var selector_height = $('#cropped_frame_selector').outerHeight();
 
   var factor  = w/selector_width; // Both are the same (or at least should be!)

   $("#cropped_frame_selector").unbind('click').click(function(e){
      /*
      var parentOffset = $(this).offset(); 
      var relX = parseFloat(e.pageX - parentOffset.left);
      var relY = parseFloat(e.pageY - parentOffset.top);

      //WARNING ONLY WORKS WITH SQUARES
      var realX = Math.floor(relX/factor+x-w/2);
      var realY = Math.floor(relY/factor+y-h/2);

      // Transform values
      if(!$(this).hasClass('done')) {
          $(this).addClass('done');
      } else {
          $('#lh').css('top',relY);
          $('#lv').css('left',relX);
          $('#meteor_pos').text("x:"+realX+'/y:'+realY);
      }
       
      //select_meteor_ajax(fn_id,realX,realY);
      */

  }).unbind('mousemove').mousemove(function(e) {
      
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left;
      var relY = e.pageY - parentOffset.top;

      console.log("IN Image ", relX, " ", relY)

      /*
      //WARNING ONLY WORKS WITH SQUARES
      var realX = relX/factor+x-w/2;
      var realY = relY/factor+y-h/2;

      // Cross
      if(!$(this).hasClass('done')) {
          $('#lh').css('top',relY-2);
          $('#lv').css('left',relX-2);
          console.log("X " + Math.floor(realX));
          console.log("Y " + Math.floor(realY));
          
             //$('#meteor_pos').text("x:"+Math.floor(realX)+'/y:'+Math.floor(realY));
           //$('#meteor_pos').text("x:"+ realX +' / y:'+ realY);
      }
      */
  });
}



// Function Init position chooser tools
function init_pos_choos() { 
  
   // Add first frame to picker
   var $first_img = $($('#cropped_frame_select').find('img').get(0))
   var $first_img_holder  = $first_img.closest('a');
  
   $('#cropped_frame_selector').css({
      'background-image':'url('+$first_img.attr('src')+')',
      'background-size':  'cover',
      'width': w + 'px',  // Defined on the page
      'height': h   + 'px' // Defined on the page
   });

   $first_img_holder.addClass('cur');

   // Fix height
   fix_pifc_ui();

   // Setup action
   setup_init_pos_choos_actions();

   // Stop loading 
   loading_done();
}


 