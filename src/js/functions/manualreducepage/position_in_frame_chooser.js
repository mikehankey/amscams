
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


// Load particular frame into the selecto
function load_frame(fd_id) {
   var $frame = $('.select_frame[data-rel='+fd_id+']');

   // Cur has changed
   $('.select_frame').removeClass('cur');
   $frame.addClass('cur');

   // Not "done" yet
   $('#cropped_frame_selector').removeClass('done');

   // We load the image
   $('#cropped_frame_selector').css({
      'background-image':'url('+$($frame.find('img')).attr('src')+')'
   }); 

   // Scroll to frame on top
   $('#frame_select_mod').scrollTo( $('.select_frame[data-rel="'+fd_id+'"]'), 150 );

   console.log("frames_done");
   console.log(frames_done);

   console.log("frames_jobs");
   console.log(frames_jobs);

   console.log("TEST IF ", fd_id , " is in ", frames_done);

   // If we already have data: we move the cross
   if($.inArray(fd_id, frames_done)) {
      console.log("YES:");
      console.log(frames_jobs[fd_id]);
   } else {
      console.log("NO");
   }
}


// Go to Next Frame
function go_to_next(next_id) {
   

   
   // TODO IF TRULY DONE!!!
   //.addClass('done');
 
   // Does the next frame exist?
   var $next_frame = $('.select_frame[data-rel='+next_id+']');
    
   if($next_frame.length != 0) {
      load_frame(parseInt(next_id));
   } else {
      // We select the first one 
      load_frame(parseInt($($('#cropped_frame_select .select_frame').get(0)).attr('data-rel')));
   }

}


// Init actions
function setup_init_pos_choos_actions() {

   var selector_width = $('#cropped_frame_selector').outerWidth();
   var selector_height = $('#cropped_frame_selector').outerHeight();
 
   var factor  = w/selector_width; // Both are the same (or at least should be!)

   // Select Frame
   $('.select_frame').unbind('click').click(function() {
      load_frame(parseInt($(this).attr('data-rel')));
   })


   // Select Meteor
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
         frames_done.push(parseInt(cur_fr_id));  // We push an int so we can get the min
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


 