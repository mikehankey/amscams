var $allImagestt; 
var animationStackDurationTT;
var timePerStackTT;
var timeWhenLastUpdateStackTT;
var timeFromLastUpdateStackTT;
var stackNumberTT; 
var animTHHplaying; 
var sensTT = "+"
 

jQuery.fn.reverse = [].reverse; 

// Modal With Player
function addAnimWeatherModalTemplate($allImagestt,cam_id) {
   
   $('#anim_ttt_modal').remove();

   $('<div id="anim_ttt_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" style="min-width:1731px;" role="document">\
   <div class="modal-content"><div class="modal-body"><div id="anim_header" class="d-flex justify-content-between"></div><div id="anim_holder">\
   </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2">\
   <div class="pt-2"><input type="range" value="1" id="marWeat" max="10" min="-10"/> <span id="cur_sp"></span></div>\
   <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
   
   // Add all the frames
   $allImagestt.each(function(i,v) {
       $(this).clone().attr('style','').addClass('to_anim to_anim-'+i).appendTo('#anim_holder');
   });

   animationStackDurationTT = 1000; //$allImagestt.length; // Duration get the 
}


// 'step' function will be called each time browser rerender the content
// we achieve that by passing 'step' as a parameter to 'requestAnimationFrame' function
function step_Anim_TT(startTime) {
  
   // 'startTime' is provided by requestAnimationName function, and we can consider it as current time
   // first of all we calculate how much time has passed from the last time when frame was update
   if (!timeWhenLastUpdateStackTT) timeWhenLastUpdateStackTT = startTime;
   timeFromLastUpdateStackTT = startTime - timeWhenLastUpdateStackTT;
 
   // then we check if it is time to update the frame
   if (timeFromLastUpdateStackTT > timePerStackTT) {
     
     $('.to_anim').css('opacity', 0); 
     $(`.to_anim-${stackNumberTT}`).css('opacity', 1);  
     timeWhenLastUpdateStackTT = startTime;
      

     if(sensTT=='+') {
         if (stackNumberTT >= totalStacks-1) {
            stackNumberTT = 0;
         } else {
            stackNumberTT = stackNumberTT + 1;
         } 
     } else {
         if (stackNumberTT <= 0) {
            stackNumberTT = totalStacks;
         } else {
            stackNumberTT = stackNumberTT - 1;
         }

     }
 
 
     //$('#cur_f').text($(`.to_anim-${stackNumberTT}`).attr('data-rel'));
     console.log("FN: " + stackNumberTT);
   }
  
   if(animTHHplaying) requestAnimationFrame(step_Anim_TT);
 }

function TT_aim() {

   var $allImagestt = $('.wi img')
 
   $allImagestt = $allImagestt.reverse();
   totalStacks  = $allImagestt.length;
   addAnimWeatherModalTemplate($allImagestt); 

   $('#anim_ttt_modal').modal();
   $('#anim_ttt_modal').on('hidden.bs.modal', function () {
        animTHHplaying = false; 
        $('#anim_ttt_modal').remove(); 
   })

   if(totalStacks==0) {
      bootbox.alert({
          message: "No weather snapshot found. Error 452b",
          className: 'rubberBand animated error',
          centerVertical: true
      });
      return false;
  }

  timePerStackTT = 1000; //animationStackDurationTT / totalStacks;
  stackNumberTT = 0; 
  animTHHplaying = true;
  requestAnimationFrame(step_Anim_TT);

  // Inpur range for animation speed
  $('#marWeat').val(0).on('input', function () { 
      var val = parseInt($(this).val()), text ='';
      if(val<0) {
         sensTT = "-";
         text = "<<";
      } 
      else {
         sensTT = "+"
         text = ">>";
      }

      if(val==0) text=''

      val+= 1;
      timePerStackTT = animationStackDurationTT*1/Math.abs(val); 
      $('#cur_sp').text(text + ' x'+val);
      requestAnimationFrame(step_Anim_TT); 
   });  
}

$(function() {
    $('#play_anim_tv').click(function(e) {
       e.stopImmediatePropagation();
       animTHHplaying = true; 
       TT_aim($(this).attr('data-rel')); 
       return false;
    });  
})

