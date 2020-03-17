

function open_meteor_picker(all_frames_ids, meteor_id, color, img_path) {

   var viewer_dim = viewer_DIM; 
   var real_width, real_height;
   var neighbor = get_neighbor_frames(meteor_id); 
   var real_width, real_height;
 
   addPickerModalTemplate(meteor_id,neighbor);
 
   // Prev Button
   $('#met-sel-prev').unbind('click').click(function() {
      meteor_select("prev",all_frames_ids);
      return false;
   });

   // Next Button
   $('#met-sel-next').unbind('click').click(function() {
      meteor_select("next",all_frames_ids);
      return false;
   });

   // Show Modal
   $('#select_meteor_modal').modal('show');

   // Add image 
   $('.meteor_chooser').css({'background-image':'url('+img_path+')','height':'100vh'}).css('border','2px solid ' + color);


   // SETUP SIZES (16/9)
   console.log("ADD 16/9");
   $('.meteor_chooser').css('height',parseInt($('.meteor_chooser').height()- $('#nav_prev').height() -$('.modal-footer').height() - 30 ));
   $('.meteor_chooser').css('width',parseInt($('.meteor_chooser').height()*16/9));
 
   // Add current ID
   $('#sel_frame_id, .sel_frame_id').text(meteor_id);

   return false;
 
 
}





function  setup_manual_reduc1() { 
   var all_frames_ids = [];

   // Only for loggedin
   if(test_logged_in()==null) {
      return false;
   }

   // Get all the frame ids
   $('#reduc-tab table tbody tr').each(function() {
       var id = $(this).attr('id');
       id = id.split('_');
       all_frames_ids.push(parseInt(id[1]));
   });

   // Click on "Big" button 
   $('.reduc1').click(function(e) { 

      // Find first id in the table
      var $tr = $('#reduc-tab table tbody tr');
      var color = $tr.find('img').css('border-color');
       
      $tr = $($tr[0]); 
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      // Then Do the all thing to open the meteor picker 
      open_meteor_picker(all_frames_ids,meteor_id,color,$tr.find('img').attr('src'));

      return false;
   });
 

   // Click on selector (thumb)
   $('.wi a').click(function(e) { 
      var $tr = $(this).closest('tr'); 
      var color = $tr.find('img').css('border-color');

      e.stopPropagation();

      // Get meteor id
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];
 
      open_meteor_picker(all_frames_ids,meteor_id,color,$tr.find('img').attr('src'));

      return false;
   });
}
