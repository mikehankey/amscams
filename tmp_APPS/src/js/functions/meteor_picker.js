function add_image_inside_meteor_select(img_path, color, all_frames_ids) {
   
      // Add image 
      var height = $('.select_meteor_holder').outerHeight() - $('#nav_prev').outerHeight() - 4;
      
      console.log("IN ADD IMG INSIDE METEOR SELECT");
      console.log(img_path);
      
      $('.meteor_chooser').css({'background-image':'url('+img_path+')','height':height - 4}).css('border','2px solid ' + color);

      // Setup 16/9 dim
      $('.meteor_chooser').css('width',parseInt($('.meteor_chooser').height()*16/9)); 
      
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
}

function open_meteor_picker(all_frames_ids, meteor_id, color, img_path) {

   var viewer_dim = viewer_DIM; 
   var real_width, real_height;
   var neighbor = get_neighbor_frames(meteor_id); 
   var real_width, real_height;
 
   addPickerModalTemplate(meteor_id,neighbor);
 
   // Show Modal if necessary
   if($('#select_meteor_modal').hasClass('show')) {
      console.log("MODAL IN") 
      add_image_inside_meteor_select(img_path, color, all_frames_ids);
   } else {
      // When the modal already exists
      console.log("MODAL NOT SHOWN")
      $('#select_meteor_modal').on('shown.bs.modal', function () {
         $('#select_meteor_modal').css('padding-right',0);
         add_image_inside_meteor_select(img_path, color, all_frames_ids);
         $('body').css('padding',0); // Because we don't want slidebars on body
      }).modal('show');
   }

  
  

  

    // Add Frame # to header
    $('#sel_frame_id').text(meteor_id);

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





// Select a meteor (next/prev arrows)
function meteor_select(dir,all_frames_ids) {
   var next_id;
   var cur_id = parseInt($('#sel_frame_id').text());
   var cur_index = all_frames_ids.indexOf(cur_id); 

   if(dir=="prev") {
       if(cur_index==0) {
           next_id = all_frames_ids.length-1;
       } else {
           next_id = cur_index - 1;
       }
   } else {
       if(cur_index==all_frames_ids.length-1) {
           next_id = 0;
       } else {
           next_id = cur_index + 1;
       }
   }  

   // Open the next or previous one
   $('#reduc-tab table tbody tr#fr_' + all_frames_ids[next_id] + " a").click();
}