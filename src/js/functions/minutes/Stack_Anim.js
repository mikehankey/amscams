// Modal With Player
function addAnimMinuteModalTemplate($allframes) {
 
   $('#anim_min_modal').remove();

   $('<div id="anim_min_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" role="document">\
   <div class="modal-content"><div class="modal-body"><div id="anim_header" class="d-flex justify-content-between"><p><b>Frame by frame animation</b></p><p><span id="cur_f"></span>/<span id="tot_f"></span> frames</p></div><div id="anim_holder">\
   </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2">\
   <div class="pt-2"><input type="range" value="1" id="mar" max="5" min="-5"/> <span id="cur_sp"></span></div>\
   <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
   
   // Add all the frames
   $allframes.each(function(i,v) {
       $(this).clone().attr('style','').addClass('to_anim to_anim-'+i).appendTo('#anim_holder');
   });

   animationDuration = $allframes.lenth / 25; // Duration get the 
   
}


// 'step' function will be called each time browser rerender the content
// we achieve that by passing 'step' as a parameter to 'requestAnimationFrame' function
function step_minute(startTime) {
 
   // 'startTime' is provided by requestAnimationName function, and we can consider it as current time
   // first of all we calculate how much time has passed from the last time when frame was update
   if (!timeWhenLastUpdate) timeWhenLastUpdate = startTime;
   timeFromLastUpdate = startTime - timeWhenLastUpdate;
 
   // then we check if it is time to update the frame
   if (timeFromLastUpdate > timePerFrame) {
     
     $('.to_anim').css('opacity', 0); 
     $(`.to_anim-${frameNumber}`).css('opacity', 1);  
     timeWhenLastUpdate = startTime;
  
     if (frameNumber >= totalFrames-1) {
       frameNumber = 0;
     } else {
       frameNumber = frameNumber + 1;
     }        
 
     $('#cur_f').text($(`.to_anim-${frameNumber}`).attr('data-rel'));
     //console.log("FN" + frameNumber);
   }
 
   if(playing) requestAnimationFrame(step_minute);
 }

function minute_anim(cam_id) {
   $allframes = $('.cam_'+cam_id);
   totalFrames = $allframes.length;
   addAnimMinuteModalTemplate($allframes);
   $('#anim_min_modal').modal();
   $('#anim_min_modal').on('hidden.bs.modal', function () {
        playing = false; 
        $('#anim_min_modal').remove(); 
   })

   if(totalFrames==0) {
      bootbox.alert({
          message: "No stack found. Error 452b",
          className: 'rubberBand animated error',
          centerVertical: true
      });
      return false;
  }

  timePerFrame = animationDuration / totalFrames;
  frameNumber = 0; 
  playing = true;

  // Inpur range for animation speed
  $('#mar').val(0).on('input', function () { 
   var val = parseInt($(this).val());

   if(val<=-1)   { 
       val-= 1; 
       timePerFrame = animationDuration*Math.abs(val) / totalFrames; 
       //$('#cur_sp').text('x'+val);
   } else if(val>=1) { 
       val+= 1;
       timePerFrame = animationDuration*1/Math.abs(val) / totalFrames; 
       //$('#cur_sp').text('x'+val);
   }
   else { 
       val=1;
       //$('#cur_sp').text('x1');
   } 
   
});  

   
  
}

$(function() {
    $('.play_anim_thumb').click(function() {
       playing = true;
       minute_anim($(this).attr('data-rel'));
    });  
})