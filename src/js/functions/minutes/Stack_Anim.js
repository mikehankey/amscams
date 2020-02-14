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

function minute_anim(cam_id) {
   $allframes = $('.cam_'+cam_id);
   totalFrames = $allframes.length;
   addAnimMinuteModalTemplate($allframes);
   $('#anim_min_modal').modal();
   $('#anim_min_modal').on('hidden.bs.modal', function () {
        playing = false; 
        $('#anim_min_modal').remove(); 
   })
}

$(function() {
    $('.play_anim_thumb').click(function() {
       playing = true;
       minute_anim($(this).attr('data-rel'));
    });  
})