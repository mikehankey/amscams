function select_one_stack(type) {
   var next_step_url = $('input[name=next_step_url]').val();

   if(type=="SD") {
      window.location = next_step_url + "&type=SD&stack=" + sd_stack + "&video=" + sd_video_file + "&json=" + json_file;
   } else {
      window.location = next_step_url + "&type=HD&stack=" + hd_stack + "&video=" + hd_video_file + "&json=" + json_file;
   }
}

function select_stack() {
   // Select a stack
   $('.select_stack').click(function() {
      
      select_one_stack(type);
 
   })


   // If the sd doesn't exist, we automatically click the HD
   if(sd_stack.indexOf('{') > -1) {
      select_one_stack("HD");
   } else if(hd_stack.indexOf('{') > -1) {
      select_one_stack("SD");
   }
} 