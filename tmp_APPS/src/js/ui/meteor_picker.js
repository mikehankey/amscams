// Modal for selector
function addPickerModalTemplate(all_frames_ids) {
   var c; 

   if($('#select_meteor_modal').length==0) {
      c ='  <div id="select_meteor_modal" class="modal fade" tabindex="-1" style="padding-right: 0!important; width: 100vw; height: 100vh;">\
                  <div class="modal-dialog  modal-lg modal-dialog-centered box" style="width: 100vw;max-width: 100%;margin: 0; padding: 0;">\
                     <div class="modal-content" style="height: 100vh;">\
                        <div class="modal-header p-0 pt-1" style="border:none!important">\
                           <h5 class="ml-1 pt-1 mb-0">Select Meteor Position  <span id="sel_frame_id"></span></h5>\
                           <div class="alert alert-info mb-0 p-1 pr-1 pl-2">Select the <strong>POSITION</strong> on the meteor on each frame.</div>\
                           <button  class="btn btn-secondary btn-sm mr-1"  data-dismiss="modal">&times; Close</button>\
                        </div>\
                        <div id="thumb_browwser" class="d-flex flex-wrap">\
                           <div class="d-flex justify-content-left" id="frame_select_mod">\
                              <div id="cropped_frame_select" class="d-flex justify-content-left">\
                                 <div>\
                                 </div>\
                              </div>\
                           </div>\
                        </div>\
                        <div id="cropped_frame_selector_hoder" class="mr-3 ml-3">\
                              <div id="cropped_frame_selector" class="cur">\
                                 <div id="org_lh"></div>\
                                 <div id="org_lv"></div>\
                                 <div id="lh"></div>\
                                 <div id="lv"></div> \
                                 <div id="cirl" style="width:20px; height:20px; border-radius:50%; position: absolute; border: 1px solid red;"></div>\
                              </div>\
                        </div>\
                        <div id="below_cfs" class="d-flex justify-content-between  m-2">\
                            <div class="alert p-1 pl-1 pr-2 mb-0"><span id="fr_cnt">0</span> Frames done</div>\
                           <div class="d-flex justify-content-center text-center">\
                              <button id="skip_frame" class="btn btn-secondary btn-sm ml-3 pr-3 pl-3">Skip</button>\
                           </div>\
                           <button id="create_all" class="btn btn-primary">Create All</button>\
                        </div>\
                     </div>\
                  </div>\
               </div>';
      $(c).appendTo('body');
    } 


   // If the frames aren't on top the of the modal, we add them
   if($('#cropped_frame_select a').length == 0 ) { 
      // Get the images from the reduc table and display them in cropped_frame_select
      $.each(all_frames_ids, function(i,v) {
         $('<a class="select_frame select_frame_btn" data-rel="'+v+'"><span>#'+v+'<i class="pos pl-1">x:? y:?</i></span><img src="'+ $('#thb_'+v).find('img').attr('src') +'"></a>').appendTo($('#cropped_frame_select div'));
      });
   }  
   
   
}



function get_neighbor_frames(cur_id) {
   // Get the thumbs & colors or -5 +5 frames
   // IN #nav_prev
   var all_thb = []; 
   cur_id = parseInt(cur_id)
   for(var i = cur_id-3; i < cur_id+4; i++) {
       var $cur_tr = $('#fr_'+i);
       var img =  $cur_tr.find('img').attr('src');
       var color = $cur_tr.find('.st').css('background-color');
       var id = i;
       vid = '';

       if(typeof img == "undefined"){
           img = './dist/img/no-sm.png';
           vid = id;
           id = '0';
       }

       if(typeof color == "undefined"){
           color = 'rgb(15,15,15)';
       } 

       all_thb.push({
           img: img,
           color:color,
           id:id,
           vid:vid
       });
   }

   return all_thb;

}

// Add Image Inside Picker
function add_image_inside_meteor_select(img_path, color, all_frames_ids, meteor_id) { 
   $('#cropped_frame_selector').css('background-image','url('+img_path+')').css('border','2px solid ' + color);


   // Add image 
   var height = $('#select_meteor_modal').outerHeight() - $('#select_meteor_modal .modal-header').outerHeight() - $("#thumb_browwser").outerHeight() - $('#below_cfs').outerHeight();
   $('#cropped_frame_selector').css('height',height- 30)
   $('#cropped_frame_selector').css('width', parseInt(height*16/9));   
   $('#sel_frame_id, .sel_frame_id').text(' - #' +  meteor_id);   


   // Add Cur to image chooser
   $('.select_frame').removeClass('cur');
   $('.select_frame[data-rel="'+meteor_id+'"]').addClass('cur');
 
   return false;
 
}


// Update Modal Template
// MAke one frame active
function updateModalTemplate(meteor_id,color,img_path,all_frames_ids) {

   console.log("updateModalTemplate")

   // Show Modal if necessary
   if($('#select_meteor_modal').hasClass('show')) { 
      console.log("--> CAS1 ");
      add_image_inside_meteor_select(img_path, color, all_frames_ids,meteor_id);
      $('#select_meteor_modal').css('padding-right',0);
      $('body').css('padding',0);
   } else {
      // When the modal already exists 
      
      console.log("--> CAS2 ");
      $('#select_meteor_modal').on('shown.bs.modal', function () {
         add_image_inside_meteor_select(img_path, color, all_frames_ids,meteor_id);
         $('#select_meteor_modal').css('padding-right',0);
         $('body').css('padding',0); // Because we don't want slidebars on body
      }).modal('show');
   }  


   $('.select_frame').unbind('click').click(function() {
      var $t = $(this);
      var MID = $t.attr('data-rel');
      var img_path = $('#thb_' + MID + " img").attr('src');
      var color =  $('#thb_' + MID + " img").css('border-color');
       

      $('#cropped_frame_selector').css('background-image','url(none)').css('border','2px solid #fff');
      add_image_inside_meteor_select(img_path,color,all_frames_ids,MID)
   });

}


// Open the Modal with a given meteor
function open_meteor_picker(meteor_id, color, img_path,all_frames_ids ) {
   updateModalTemplate(meteor_id,color,img_path,all_frames_ids);
   return false; 
} 



/*******************************
 * MAIN SETUP
 **/

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
  
   // Add modal Template 
   addPickerModalTemplate(all_frames_ids); 

   // Click on "Big" button 
   $('.reduc1').click(function(e) { 

      // Find first id in the table
      var $tr = $('#reduc-tab table tbody tr');
      var color = $tr.find('img').css('border-color');
 
       
      $tr = $($tr[0]); 
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];

      // Then Do the all thing to open the meteor picker 
      open_meteor_picker(meteor_id,color,$tr.find('img').attr('src'),all_frames_ids);

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
 
      open_meteor_picker(meteor_id,color,$tr.find('img').attr('src'),all_frames_ids);


      return false;
   });
}