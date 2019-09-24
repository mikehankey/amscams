
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
   $('#org_lv, #lw').css('height','100%');

}


function setup_init_pos_choos_actions() {

   var selector_width = $('#cropped_frame_selector').outerWidth();
   var selector_height = $('#cropped_frame_selector').outerHeight();
 
   var factor_H = w/selector_width;
   var factor_W = h/selector_height;

   console.log("FACTOR H " + factor_H);
   console.log("FACTOR W " + factor_W);
   



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


 