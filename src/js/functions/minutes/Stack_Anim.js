

function minute_anime(cam_id) {
   $allframes = $('.cam_'+cam_id);
   totalFrames = $allframes.length;
   addAnimModalTemplate($allframes);
   $('#anim_modal').modal();
   $('#anim_modal').on('hidden.bs.modal', function () {
        playing = false; 
        $('#anim_modal').remove(); 
   })
}

$(function() {
    $('.play_anim_thumb').click(function() {
       playing = true;
       minute_anim($(this).attr('data-rel'));
    });  
})