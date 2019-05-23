

function reject_meteor(id) {
   var m = "clicked: " + id;
   new_id = 'fig_' + id
   $('#' + new_id).remove();
   ajax_url = "webUI.py?cmd=override_detect&jsid=" + id
   $.get(ajax_url, function(data) {
         $(".result").html(data);
      });
}

function play_meteor_video (video_url) {
   $('#ex1').modal();
   $('#v1').attr("src", video_url);
}
