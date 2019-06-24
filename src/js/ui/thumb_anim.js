var $allthumbs;
var totalThumbs;
var animationThumbDuration;
var timePerThumb;
var timeWhenLastUpdateThumb;
var timeFromLastUpdateThumb;
var thumbNumber; 
var thumbPlaying;

// Modal for selector
function addAnimThumbModalTemplate($allthumbs) {
    var realDur    = 10;
    var dur_unknow = false;

    if(isNaN(realDur)) {
        realDur = 1; // 1 second default
        dur_unknow= true;
    }

    $('#anim_modal').remove();

    $('<div id="anim_modal" class="modal fade" tabindex="-1" role="dialog"><div class="modal-dialog modal-dialog-centered" role="document">\
    <div class="modal-content"><div class="modal-body"><div id="anim_header" class="d-flex justify-content-between"><p><b>Frame by frame animation</b></p><p><span id="cur_f"></span>/<span id="tot_f"></span> frames</p></div><div id="anim_holder" style="height:326px">\
    </div><div class="modal-footer d-flex justify-content-between p-0 pb-2 pr-2">\
    <div class="pt-2"><input type="range" value="1" id="mar" max="5" min="-5"/> <span id="cur_sp"></span></div>\
    <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button></div></div></div></div>').appendTo('body');
    
    // Add all the frames
    $allthumbs.each(function(i,v) {
        $(this).clone().addClass('to_anim to_anim-'+i).appendTo('#anim_holder');
    });

    animationThumbDuration = realDur*1000; // Duration get the 

    if(dur_unknow) {
        $('#alert_anim').remove();
        $('<div id="alert_anim" class="alert alert-danger">Unknown Real Duration</div>').insertAfter($('#anim_header'));
    } 
}

function thumb_anim() { 
    
    $allthumbs = $('img.lz');
    totalThumbs = $allthumbs.length;
    
    addAnimThumbModalTemplate($allthumbs);
    $('#anim_modal').modal();
    $('#anim_modal').on('hidden.bs.modal', function () {
        thumbPlaying = false; 
        $('#anim_modal').remove(); 
    })

    if(totalThumbs==0) {
        bootbox.alert({
            message: "No frame found. Reduce the meteor first",
            className: 'rubberBand animated error',
            centerVertical: true
        });
        return false;
    }
  
    timePerThumb = animationThumbDuration / totalThumbs;
    thumbNumber = 0; 
    thumbPlaying = true;
     

    $('#tot_f').text(totalThumbs);
    $('#cur_sp').text('x1');

    $('#mar').val(0).on('input', function () { 
        var val = parseInt($(this).val());
 
        if(val<=-1)   { 
            val-= 1; 
            timePerThumb = animationThumbDuration*Math.abs(val) / totalThumbs; 
            $('#cur_sp').text('x'+val);
        } else if(val>=1) { 
            val+= 1;
            timePerThumb = animationThumbDuration*1/Math.abs(val) / totalThumbs; 
            $('#cur_sp').text('x'+val);
        }
        else { 
            val=1;
            $('#cur_sp').text('x1');
        } 
        
    });  
    requestAnimationFrame(step);
}
  

// 'step' function will be called each time browser rerender the content
// we achieve that by passing 'step' as a parameter to 'requestAnimationFrame' function
function step(startTime) {
 
  // 'startTime' is provided by requestAnimationName function, and we can consider it as current time
  // first of all we calculate how much time has passed from the last time when frame was update
  if (!timeWhenLastUpdateThumb) timeWhenLastUpdateThumb = startTime;
  timeFromLastUpdateThumb = startTime - timeWhenLastUpdateThumb;

  // then we check if it is time to update the frame
  if (timeFromLastUpdateThumb > timePerThumb) {
    
    $('.to_anim').css('opacity', 0); 
    $(`.to_anim-${thumbNumber}`).css('opacity', 1);  
    timeWhenLastUpdateThumb = startTime;
 
    if (thumbNumber >= totalThumbs-1) {
      thumbNumber = 0;
    } else {
      thumbNumber = thumbNumber + 1;
    }        

    $('#cur_f').text(thumbNumber);
  }

  if(thumbPlaying) requestAnimationFrame(step);
}
 
$(function() {
    $('#play_anim_thumb').click(function() {
       thumbPlaying = true;
       thumb_anim();
    });

   
      
})