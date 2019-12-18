$(function() {

   // Go to manual sync
   $('#manual_synchronization').click(function(){


      stack_file = form.getvalue('stack')
      video_file = form.getvalue('video')
      type_file  = form.getvalue('type')    # HD or SD
      json_file  = form.getvalue('json')

      window.location = './webUI.py?cmd=manual_sync&json_file=' + json_file +'&video_file=' + main_vid + '&stack_file=' + my_image + '&type_file=HD'
   })

})
