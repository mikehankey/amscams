
var frames_done=[];  // Just for the frames done
var frames_jobs=[];  // All the info for the frames done
var select_border_size = 3; // See css

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


// Go to Next Frame
function go_to_next(next_id) {
   
   // Mark frame as done
   $('#cropped_frame_select .cur').removeClass('cur').addClass('done');

   // Scroll to frame on top
   $('#frame_select_mod').scrollTo( $('.select_frame[data-rel="'+next_id+'"]'), 800 );

   // Does the next frame exist?
   var $next_frame = $('.select_frame[data-rel='+next_id+']');
   console.log("NEXT FRAME ", $next_frame);

   if($next_frame.length != 0) {
      
      // We select the next one
      $('#cropped_frame_selector').css({
         'background-image':'url('+$($next_frame.find('img')).attr('src')+')'
      });

      $next_frame.addClass('cur'); 

   } else {
      // We select the first one 
      var $first_img = $($('#cropped_frame_select').find('img').get(0))
      var $first_img_holder  = $first_img.closest('a');
     
      $('#cropped_frame_selector').css({'background-image':'url('+$first_img.attr('src')+')'});
   }

}


// Init actions
function setup_init_pos_choos_actions() {

   var selector_width = $('#cropped_frame_selector').outerWidth();
   var selector_height = $('#cropped_frame_selector').outerHeight();
 
   var factor  = w/selector_width; // Both are the same (or at least should be!)

   $("#cropped_frame_selector").unbind('click').click(function(e){
     
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;

      // Convert into HD_x & HD_y
      // from x,y
      var realX = relX*factor+x;
      var realY = relY*factor+y;
 
      // Transform values
      if(!$(this).hasClass('done')) {
          $(this).addClass('done');
      } else {
          $('#lh').css('top',relY);
          $('#lv').css('left',relX);
          $('#meteor_pos').text("x:"+realX+'/y:'+realY);
      }
 
      cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');

      // Add current frame to frame_done if not already there
      if($.inArray(cur_fr_id, frames_done )==-1) {
         frames_done.push(cur_fr_id);
      }

      // Add info to frames_jobs
      frames_jobs[cur_fr_id] = {
         'fn': cur_fr_id,
         'x': realX,
         'y': realY
      };
      
      // Add info to frame scroller
      $('#cropped_frame_select .cur span').html($('#cropped_frame_select .cur span').html() + '<br>x:' + parseInt(realX) + ' y:'  + parseInt(realY));
      
      // Go to next frame
      go_to_next(parseInt(cur_fr_id)+1);
      
  }).unbind('mousemove').mousemove(function(e) {
      
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;

      // Cross
      if(!$(this).hasClass('done')) {
          $('#lh').css('top',relY-2);
          $('#lv').css('left',relX-2); 
      }
       
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


 