

function open_meteor_picker(all_frames_ids, meteor_id, color, img_path) {

   var viewer_dim = viewer_DIM; 
   var real_width, real_height;
   var neighbor = get_neighbor_frames(meteor_id); 
   var real_width, real_height;
   addModalTemplate(meteor_id,neighbor);
 
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

   return false;
 

   // Click on selector (button & thumb)
   $('.select_meteor').click(function(e) {

        e.stopImmediatePropagation();
 
       var $tr = $(this).closest('tr');
       var rand;

       // Get meteor id
       var meteor_id = $tr.attr('id');
       meteor_id = meteor_id.split('_')[1];
 
       // Get Image
       var $img = $tr.find('img'); 

       // Get Color
       var color = $tr.find('.st').css('background-color');

       var real_width, real_height;

       // Get Neightbors
       

       // Add template if necessary
       addModalTemplate(meteor_id,neighbor);

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

       // Add image 
       $('.meteor_chooser').css('background-image','url('+$img.attr('src')+')').css('border','2px solid ' + color);
       
       
       // Add current ID
       $('#sel_frame_id, .sel_frame_id').text(meteor_id);

     
       // Update image real dimensions 
       var img = new Image();
       var imgSrc = $img.attr('src');

       $(img).on('load',function () {
           real_width = img.width;
           real_height = img.height;
           $('input[name=thumb_w]').val(real_width);
           $('input[name=thumb_h]').val(real_height); 
           // garbage collect img
           delete img;

           // Redefine viewer depending on the thumb dimension
           if(real_width !== real_height) {
           
               if(real_width > real_height) {
                   $('.meteor_chooser').css('height',  real_height/real_width * viewer_dim);
               } else {
                   $('.meteor_chooser').css('width', real_width/real_height * viewer_dim);
               }

           } else {
               $('.meteor_chooser').css({'height': viewer_dim + 'px', 'width':viewer_dim + 'px'});
           }
            
           // Reset Cross position
           $('#lh').css('top','50%');
           $('#lv').css('left','50%');
           
           // Open Modal
           $('#select_meteor_modal').modal('show');

           // Reset
           $(".meteor_chooser").removeClass('done'); 
           setup_modal_actions(meteor_id, $tr.attr('data-org-x'),$tr.attr('data-org-y'));

        
       }).attr({ src: imgSrc }); 

       return false;
       

   });
}





function  setup_manual_reduc1() { 
   var all_frames_ids = [];

   // Get all the frame ids
   $('#reduc-tab table tbody tr').each(function() {
       var id = $(this).attr('id');
       id = id.split('_');
       all_frames_ids.push(parseInt(id[1]));
   });

   // Click on "Big" button 
   $('.reduc1').click(function(e) {
 
      console.log(".reduc1");

      // Find first id in the table
      var $tr = $('#reduc-tab table tbody tr');
      var color = $tr.find('img').css('border-color');
      
      e.stopPropagation();
 
      $tr = $($tr[0]); 
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      // Then Do the all thing to open the meteor picker 
      open_meteor_picker(all_frames_ids,meteor_id,color,$tr.find('img').attr('src'));
   });
 

   // Click on selector (thumb)
   $('.wi a').click(function(e) {
      
      console.log(".wi a");


      var $tr = $(this).closest('tr'); 
      var color = $tr.find('img').css('border-color');

      e.stopPropagation();

      // Get meteor id
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      
      open_meteor_picker(all_frames_ids,meteor_id,color,$tr.find('img').attr('src'));
   });
}
