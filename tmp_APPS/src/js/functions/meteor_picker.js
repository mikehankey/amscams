function add_image_inside_meteor_select(img_path, color, all_frames_ids,meteor_id) {
   
      // Add image 
      var height = parseInt($('.select_meteor_holder').outerHeight() - $('#nav_prev').outerHeight() - 4);
     
      
      $('.meteor_chooser').css({'background-image':'url('+img_path+')','height':height}).css('border','2px solid ' + color);

      // Setup 16/9 dim
      $('.meteor_chooser').css('width', parseInt($('.meteor_chooser').outerHeight()*16/9)); 
      $('.meteor_chooser').css('height', ($('.meteor_chooser').width()*9/16)+4); // 4 = borders 
      
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

      // Select top miniature
      $('.ccur').removeClass('ccur');
      $('a[data-m="'+meteor_id+'"]').parent().addClass('ccur');


      console.log("INIT WIDTH " + $('.meteor_chooser').width())
      console.log("INIT HEIGHT " + $('.meteor_chooser').height())
      console.log("FROM WIDTH " + ($('.meteor_chooser').width()*9/16) )
}

function open_meteor_picker(all_frames_ids, meteor_id, color, img_path) {
 
   var neighbor = get_neighbor_frames(meteor_id);  
   addPickerModalTemplate(meteor_id,neighbor);
 
   // Show Modal if necessary
   if($('#select_meteor_modal').hasClass('show')) { 
      add_image_inside_meteor_select(img_path, color, all_frames_ids,meteor_id);
   } else {
      // When the modal already exists 
      $('#select_meteor_modal').on('shown.bs.modal', function () {
         add_image_inside_meteor_select(img_path, color, all_frames_ids,meteor_id);
         $('#select_meteor_modal').css('padding-right',0);
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