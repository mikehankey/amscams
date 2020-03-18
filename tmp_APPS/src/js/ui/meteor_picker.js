

// Modal for selector
function addPickerModalTemplate(all_frames_ids, meteor_id) {
   var c;
    
   if($('#select_meteor_modal').length==0) {
      c ='  <div id="select_meteor_modal" class="modal fade" tabindex="-1" style="padding-right: 0!important; display: block; width: 100vw; height: 100vh;>\
                  <div class="modal-dialog  modal-lg modal-dialog-centered box" style="width: 100vw;max-width: 100%;margin: 0; padding: 0;">\
                     <div class="modal-content" style="height: 100vh;">\
                        <div class="modal-header p-0 pt-1" style="border:none!important">\
                           <h5 class="ml-1">Select Meteor Position</h5>\
                           <div class="alert alert-info mb-3 p-1 pr-1 pl-2">Select the <strong>POSITION</strong> on the meteor on each frame.</div>\
                           <div class="alert p-1 pl-1 pr-2"><span id="fr_cnt">0</span> Frames done</div>\
                        </div>\
                        <div class="d-flex flex-wrap">\
                           <div class="d-flex justify-content-left" id="frame_select_mod">\
                              <div id="cropped_frame_select" class="d-flex justify-content-left">\
                                 <div>\
                                 </div>\
                              </div>\
                           </div>\
                        </div>\
                        <div id="cropped_frame_selector_hoder" class="mt-3 mb-2">\
                              <div id="cropped_frame_selector" class="cur">\
                                 <div id="org_lh"></div>\
                                 <div id="org_lv"></div>\
                                 <div id="lh"></div>\
                                 <div id="lv"></div> \
                                 <div id="cirl" style="width:10px; height:10px; border-radius:50%; position: absolute; border: 1px solid red;"></div>\
                              </div> \
                        </div>\
                        <div class="d-flex justify-content-between">\
                           <button  class="btn btn-primary hidden" style="visibility: hidden;">Create All</button>\
                           <div class="d-flex justify-content-center text-center">\
                              <button id="skip_frame" class="btn btn-secondary ml-3">Skip</button>\
                           </div>\
                           <button id="create_all" class="btn btn-primary">Create All</button>\
                        </div>\
                        </div>\
                     </div>\
                  <div class="modal-footer bd-t mt-3 pt-2 pb-2 pr-2">\
                     <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
                  </div>\
               </div>';
      $(c).appendTo('body');
    } 


   // If the frames aren't on top the of the modal
   if($('#cropped_frame_select a').length==0) {
      // Get the images from the reduc table and display them in cropped_frame_select
      $.each(all_frames_ids, function(i,v) {
         $('<a class="select_frame select_frame_btn done" data-rel="'+v+'"><span>HD#="'+v+'"<i class="pos"><br>x:? y:?</i></span><img src="'+ $('#thb_'+v).find('img').attr('src')+'"></a>
      });
   }  
   
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