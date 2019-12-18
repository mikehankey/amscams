$(function() {

   // Go to manual sync step 1
   $('#manual_synchronization').click(function(){ 
      window.location = './webUI.py?cmd=manual_sync&json_file=' + json_file +'&video_file=' + main_vid + '&stack_file=' + my_image + '&type_file=HD'
   })

})
