function select_start_frame() {
   $('.frame_selector').click(function(e) {
      var selected_frame = $(this).attr('data-rel');
      window.location = './webUI.py?cmd=manual_reduction_meteor_pos_selector&video_file='+video_file+'&x='+x+'&y='+y+'&w='+w+'&h='+h+'&f='+selected_frame
   })
}
 