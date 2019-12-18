$(function() {

   // Go to manual sync
   $('#manual_synchronization').click(function(){
      window.location = './webUI.py?cmd=manual_sync&json_file=' + json_file
   })

})
