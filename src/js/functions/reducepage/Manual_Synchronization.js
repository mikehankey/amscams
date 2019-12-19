$(function() {

   // Go to manual sync step 1
   $('#manual_synchronization').click(function(){ 
      window.location = './webUI.py?cmd=manual_sync&json=' + json_file +'&video=' + main_vid + '&stack=' + my_image + '&type=HD'
   })

})
