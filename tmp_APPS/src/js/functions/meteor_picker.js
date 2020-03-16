function  setup_manual_reduc1() { 
   var all_frames_ids = [];

   // Get all the frame ids
   $('#reduc-tab table tbody tr').each(function() {
       var id = $(this).attr('id');
       id = id.split('_');
       all_frames_ids.push(parseInt(id[1]));
   });

   // Click on "Big" button 
   $('.reduc1').click(function() {
      // Find first id in the table
      var $tr = $('#reduc-tab table tbody tr');
      $tr = $($tr[0]); 
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      // Then Do the all thing to open the meteor picker 
      open_meteor_picker(meteor_id);
   });
 

   // Click on selector (thumb)
   $('.wi a').click(function() {
      var $tr = $(this).closest('tr'); 
      // Get meteor id
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];
      open_meteor_picker(meteor_id);
   });
}
