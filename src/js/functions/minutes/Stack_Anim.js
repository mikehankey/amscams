var $allstacks;
var totalStacks;
var animationStackDuration;
var timePerStack;
var timeWhenLastUpdateStack;
var timeFromLastUpdateStack;
var stackNumber; 
var stackplaying; 

// Modal With Player
function addAnimMinuteModalTemplate($allstacks) {
 
   $('#anim_min_modal').remove();

   $('<div id="anim_min_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" role="document">\
   <div class="modal-content"><div class="modal-body"><div id="anim_header" class="d-flex justify-content-between"><p><b>Stack animation</b> Cam#</p><p><span id="cur_f"></span></p></div><div id="anim_holder">\
   </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2">\
   <div class="pt-2"><input type="range" value="1" id="marStack" max="10" min="-10"/> <span id="cur_sp"></span></div>\
   <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
   
   // Add all the frames
   $allstacks.each(function(i,v) {
       $(this).clone().attr('style','').addClass('to_anim to_anim-'+i).appendTo('#anim_holder');
   });

   animationStackDuration = $allstacks.length; // Duration get the 
}


// 'step' function will be called each time browser rerender the content
// we achieve that by passing 'step' as a parameter to 'requestAnimationFrame' function
function step_minute(startTime) {
 
 
   // 'startTime' is provided by requestAnimationName function, and we can consider it as current time
   // first of all we calculate how much time has passed from the last time when frame was update
   if (!timeWhenLastUpdateStack) timeWhenLastUpdateStack = startTime;
   timeFromLastUpdateStack = startTime - timeWhenLastUpdateStack;
 
   // then we check if it is time to update the frame
   if (timeFromLastUpdateStack > timePerStack) {
     
     $('.to_anim').css('opacity', 0); 
     $(`.to_anim-${stackNumber}`).css('opacity', 1);  
     timeWhenLastUpdateStack = startTime;
  
     if (stackNumber >= totalStacks-1) {
       stackNumber = 0;
     } else {
       stackNumber = stackNumber + 1;
     }        
 
     $('#cur_f').text($(`.to_anim-${stackNumber}`).attr('data-rel'));
     //console.log("FN" + stackNumber);
   }
 
   if(stackplaying) requestAnimationFrame(step_minute);
 }

function minute_anim(cam_id) {
   $allstacks = $('.cam_'+cam_id);
   $allstacks = $allstacks.reverse();
   totalStacks = $allstacks.length;
   addAnimMinuteModalTemplate($allstacks);
   $('#anim_min_modal').modal();
   $('#anim_min_modal').on('hidden.bs.modal', function () {
        stackplaying = false; 
        $('#anim_min_modal').remove(); 
   })

   if(totalStacks==0) {
      bootbox.alert({
          message: "No stack found. Error 452b",
          className: 'rubberBand animated error',
          centerVertical: true
      });
      return false;
  }

  timePerStack = 2;
  stackNumber = 0; 
  stackplaying = true;
  requestAnimationFrame(step_minute);

  // Inpur range for animation speed
  $('#marStack').val(0).on('input', function () { 
   var val = parseInt($(this).val());

   if(val<=-1)   { 
       val-= 1; 
       timePerStack = animationStackDuration*Math.abs(val) / totalStacks; 
       $('#cur_sp').text('x'+val);
   } else if(val>=1) { 
       val+= 1;
       timePerStack = animationStackDuration*1/Math.abs(val) / totalStacks; 
       $('#cur_sp').text('x'+val);
   }
   else {  
       val=1;
       $('#cur_sp').text('x1');
   } 
   
   requestAnimationFrame(step_minute);
});  

   
  
}

$(function() {
    $('.play_anim_thumb').click(function() {
       stackplaying = true;
       minute_anim($(this).attr('data-rel'));
    });  
})