var frames_jobs=[];           // All the info for the frames updated/created
var select_border_size = 2;   // See css 
var frames_done=[];           // Just for the frames # of the frames updated/created 
var circle_radius = 40;       // See css
var thumb_width = 200;        // See px css
var margin_thumb= 0.24        // See rem css
var FPS = 25;                 // For duration
var first_frame, last_frame;  // To send to the API


var tmp_JSON; // Copy of the original JSON used to store all the updates

// We need the min & max cropped to set the clip length
var all_cropped_frames_ids = []; // FROM THE JSON

// Set up green line for clip lenght (start/end are frame ids)
function setClipLength(from,to) { 
   to = to +1; // Because UI / CSS
   // Start:
   var marg = "calc(("+thumb_width+"px + "+margin_thumb+"rem) * "+ from +") ";
   // End:
   var width = "calc(("+thumb_width+"px + "+margin_thumb+"rem) * "+ (to-from) +") ";
 
   $('.clip_length').css('margin-left',marg).css('width',width);

   // Update length_info
   $('#length_info').html('- duration: ' + (to-from) + " frames (" +  ((to-from)  /  FPS).toFixed(2) + "s)");

   first_frame = from;
   last_frame = to-1; // Because UI / CSS
}


// Find & Setup new clip length
// Based on new onces and the original in the JSON
function getNewClipLengthAndUpdate() {

   // We get the min/max from frames_done
   var _min = Math.min.apply(Math,frames_done);
   var _max = Math.max.apply(Math,frames_done);

   // And from all_cropped_frames_ids
   _min = Math.min(_min,Math.min.apply(Math,all_cropped_frames_ids));
   _max = Math.max(_max,Math.max.apply(Math,all_cropped_frames_ids));

   setClipLength(_min,_max); 
}


// Modal for selector
function addPickerModalTemplate(all_cropped_frames) {
   var c;  

   if($('#select_meteor_modal').length==0) {
      c ='  <div id="select_meteor_modal" class="modal fade" tabindex="-1" style="padding-right: 0!important; width: 100vw; height: 100vh;">\
                  <div class="modal-dialog  modal-lg modal-dialog-centered box" style="width: 100vw;max-width: 100%;margin: 0; padding: 0;">\
                     <div class="modal-content" style="height: 100vh;">\
                        <div class="modal-header p-0 pt-1" style="border:none!important">\
                           <h5 class="ml-1 pt-1 mb-0">Select Meteor Position  <span id="sel_frame_id"></span> <span id="length_info"></span></h5>\
                           <button  class=" close pt-3 pr-2 mr-1" data-dismiss="modal">&times;</button>\
                        </div>\
                        <div id="thumb_browwser" class="d-flex flex-wrap">\
                           <div class="d-flex justify-content-left mr-2 ml-2 mb-2" id="frame_select_mod">\
                              <div id="cropped_frame_select" class="d-flex justify-content-left position-relative">\
                                 <div id="clip" class="mt-1" >\
                                    <div class="clip_length " ></div>\
                                 </div>\
                                 <div class="ffs mt-1">\
                                 </div>\
                              </div>\
                           </div>\
                        </div>\
                        <div id="cropped_frame_selector_hoder" class="mr-3 ml-3">\
                              <div id="cropped_frame_selector" class="cur">\
                              </div>\
                        </div>\
                        <div id="below_cfs" class="d-flex justify-content-between  m-2">\
                           <div class="alert p-1 pl-1 pr-2 mb-0"><span id="fr_cnt">0</span> Frames done</div>\
                           <div class="d-flex justify-content-center text-center">\
                              <button id="delete_b_cur" class="btn btn-danger mr-2"><i class="icon-circle-left"></i> Delete all frames before</button>\
                              <button id="delete_a_cur" class="btn btn-danger ml-2">Delete all frames after <i class="icon-circle-right"></i></button>\
                           </div>\
                           <button id="create_all" class="btn btn-primary">Create All</button>\
                        </div>\
                     </div>\
                  </div>\
               </div>';
      $(c).appendTo('body');
    } 


   // If the frames aren't on top the of the modal, we add them (INIT)
   if($('#cropped_frame_select a').length == 0 ) { 
   
      // Get the images from all_cropped_frames and add them
      $.each(all_cropped_frames, function(i,v) {

         var data = "";
         var _class="";

         // Is the frame already in the json?
         res = get_data_from_json(i)
         if(res!= false) {
            data = '<i class="pos">x:'+ res['org_x'] + ' y:'+ res['org_y'] +'</i>';
            _class = "exists"
            all_cropped_frames_ids.push(i)
         }
  
         $('<a class="select_frame select_frame_btn '+_class+'" data-rel="'+i+'"><span>#'+i+'  &bull; '+data+'</span><img src="'+  v  +'"></a>').appendTo($('#cropped_frame_select div.ffs'));

      });


      // We set the initial clip length 
      setClipLength( Math.min.apply(Math,all_cropped_frames_ids), Math.max.apply(Math,all_cropped_frames_ids));
 
   }   
}



// Go to Next Frame
function go_to_next(next_id) {
 
   // Does the next frame exist?
   var $next_frame = $('.select_frame[data-rel='+next_id+']');
   
   // we get the related src path

   if($next_frame.length != 0) {
      add_frame_inside_meteor_select($next_frame.find('img').attr('src'), parseInt(next_id))
   } else {
      // We select the first one 
      var next_id = parseInt($($('#cropped_frame_select .select_frame').get(0)).attr('data-rel'));
      $next_frame = $('.select_frame[data-rel='+next_id+']');
 
      add_frame_inside_meteor_select($next_frame.find('img').attr('src'),next_id);
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


// Add Circle Repair
function addCircleRepair(_x,_y,fn,after_of_before) {
   var $cir = $('<div class="circl"><span>'+fn+'</span></div>');

   $('#cropped_frame_selector').append($cir);
   $cir.css({
      'left': parseInt(_x-(circle_radius/2)) + 'px',
      'top':  parseInt(_y-(circle_radius/2)) + 'px' 
   });

   if(after_of_before=='b') {
      $cir.css('border-color','rgba(255, 0, 0, .3)');
   } else if(after_of_before =='x') {
      // Current
      $cir.css('border-color','rgba(255, 229, 46, .12)');
   } else if(after_of_before == 'na' || after_of_before == 'nb') {
      $cir.css('border-color','rgba(25, 86, 189,.4)'); // Done
   } else {
      $cir.css('border-color','rgba(0, 255, 0, .3)');
   }
   
}



// Function add to debug div
function add_debug(msg) {
   if($('#action').html()=='') {
      $('#action').html(msg);
   } else {
      $('#action').html($('#action').html()+"<br>"+ msg);
   }
}

// Function add Mouse pos
function add_mouse_pos(_x,_y,factor) {
   $('#mouse_pos').html("Mouse pos (loc):" + _x + " , " + _y + "<br>Mouse pos (rel):" + (_x+x) + " , " + (_y+y));
}


// Change Local x,y to Real x,y
function convert_from_local(_x,_y) {
   return [(_x+x), (_y+y)];
}


// Change REAL x,y to LOCAL x,y
function convert_to_local(_x,_y) {
   return [(_x-x), (_y-y)];
}



// Return x & y or false  for a given frame id in frames_jobs
function get_new_pos(frame_id) {
   var t = false, res=[];
   
   $(frames_jobs).each(function(i,v) {
      if(v['fn']==frame_id) {
         t = true;
         res = [v['x'],v['y']];
      }
   })

   if(t==true) {
      return res;
   } else {
      return false;
   }
 

}




// Delete all frames before one
function delete_before() {
 
   // Delete BEFOPRE
   $('#delete_b_cur').unbind('click').click(function(e) {
   
      // Cur frame
      var cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');
      var new_first_frame = parseInt(cur_fr_id)-1;

      // => it means cur_fr_id == FIRST FRAME! 
      if((last_frame-new_first_frame)<=1) {
         bootbox.alert({
            message: "Error: you need at least 2 frames for the detection",
            className: 'rubberBand animated error',
            centerVertical: true 
         })
         return false;
      } else {
         
         // We need to remove all the data from frames_done and frames_jobs for the remove frames
         // ie the frames from first_frame to new_first_frame
         first_frame  = new_first_frame+1;

         // UI (remove pos & class exists)
         $('.select_frame.exists').each(function(i,v) {
            var id = parseInt($(v).attr('data-rel'));
            if(id<first_frame) {  
               $('.select_frame[data-rel='+id+']').removeClass('exists');
               $('.select_frame[data-rel='+id+']').find('.pos').remove();
               delete_frame_from_json(id);
            }
         });

         setClipLength(first_frame,last_frame);

         // Update the circles on the current view
         $('.select_frame[data-rel='+cur_fr_id+'] ').click();
      }
   });
}


// Delete all frames after one
function delete_after() {
   // Delete BEFOPRE
   $('#delete_a_cur').unbind('click').click(function(e) {
         
      // Cur frame
      var cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');
      var new_last_frame = parseInt(cur_fr_id)+1;

      // => it means cur_fr_id == FIRST FRAME! 
      if((new_last_frame-first_frame)<=1) {
         bootbox.alert({
            message: "Error: you need at least 2 frames for the detection",
            className: 'rubberBand animated error',
            centerVertical: true 
         })
         return false;
      } else {
         
         // We need to remove all the data from frames_done and frames_jobs for the remove frames
         // ie the frames from first_frame to new_first_frame
         last_frame  = new_last_frame-1;

         // UI (remove pos & class exists)
         $('.select_frame.exists').each(function(i,v) {
            var id = parseInt($(v).attr('data-rel'));
            if(id>last_frame) { 
               $('.select_frame[data-rel='+id+']').removeClass('exists');
               $('.select_frame[data-rel='+id+']').find('.pos').remove();
               delete_frame_from_json(id);
            }
         });

         setClipLength(first_frame,last_frame);

         // Update the circles on the current view
         $('.select_frame[data-rel='+cur_fr_id+'] ').click();

      }
   });
}

// Select meteor position (ui)
function select_meteor_pos(factor) {

   delete_before();
   delete_after();

   // Select Meteor
   $("#cropped_frame_selector").unbind('click').click(function(e){
     
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;
      var cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');
   
      // Convert into HD_x & HD_y
      // from x,y
      var realX = relX*factor+x;
      var realY = relY*factor+y;
   
      // Transform values
      if(!$(this).hasClass('done')) {
          $(this).addClass('done');
      }  
   
      // Add current frame to frame_done if not already there
      if($.inArray(cur_fr_id, frames_done )==-1) {
         frames_done.push(parseInt(cur_fr_id));  // We push an int so we can get the min
         $('#fr_cnt').html(parseInt($('#fr_cnt').html())+1);
      }
   
      // Add info to frames_jobs
      frames_jobs.push({
         'fn': cur_fr_id,
         'x': Math.round(realX),
         'y': Math.round(realY)
      });
      

      // Update Clip length
      getNewClipLengthAndUpdate();

      // Add info to frame scroller
      $('.select_frame[data-rel='+cur_fr_id+']').addClass('done').addClass('updated').find('span').html('#'+cur_fr_id+'  &bull;<br>x:' + parseInt(realX) + ' y:'  + parseInt(realY));
      
      // Go to next frame
      go_to_next(parseInt(cur_fr_id)+1);
      
   }).unbind('mousemove').mousemove(function(e) {
      
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size; 

      add_mouse_pos(parseInt(relX*factor),parseInt(relY*factor),factor);
   
   });
   
}




// Add circles (after, before & current)
// for a given frame 
function add_all_circles(meteor_id, factor) {
   // Remove All Circles
   $('.circl').remove();

   // Is the CURRENT frame in the JSON?
   // WARNING HERE WE PASS METEOR_ID 
   
   // Do we have a "new pos"
   test_new_pos = get_new_pos(meteor_id);
   if(test_new_pos != false) {
      xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 
      addCircleRepair(xy[0]/factor,xy[1]/factor,meteor_id,'x'); 
   } else {
      // Of something in the initial JSON?
      res = get_data_from_json(meteor_id)
      if(res != false) {
         xy = convert_to_local(parseInt(res['org_x']),parseInt(res['org_y'])); 
         addCircleRepair(xy[0]/factor,xy[1]/factor,meteor_id,'x'); 
      }
   }


   HOW_MANY_AFTER_AND_BEFORE = 1;

   // Do we have previous frames in the JSON?
   for(var i = (meteor_id-1); i >= meteor_id - HOW_MANY_AFTER_AND_BEFORE ; i--) {
      
      // First we test if we have a new position  
      test_new_pos = get_new_pos(i);
      if(test_new_pos != false) {
            xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 
            addCircleRepair(xy[0]/factor,xy[1]/factor,i,'nb'); 
      } else {
         
         // or an old one...
         res = get_data_from_json(parseInt(i));
         if(res != false) {
            xy = convert_to_local(parseInt(res['org_x']),parseInt(res['org_y'])); 
            addCircleRepair(xy[0]/factor,xy[1]/factor,i,'b'); 
         }
      }

   }

   // Do we have next frames in JSON?
   for(var i = (meteor_id+1); i <= meteor_id + HOW_MANY_AFTER_AND_BEFORE ; i++) { 
      
      test_new_pos = get_new_pos(i);
      if(test_new_pos != false) {
            xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 
            addCircleRepair(xy[0]/factor,xy[1]/factor,i,'nb'); 
      } else {
      
         res = get_data_from_json(parseInt(i)); 

         if(res != false) {
            xy = convert_to_local(parseInt(res['org_x']),parseInt(res['org_y'])); 
            addCircleRepair(xy[0]/factor,xy[1]/factor,i,'a'); 
         }
      }
   }    
}



// Add Image Inside Picker
function add_frame_inside_meteor_select(img_path, meteor_id) { 
 
   // Scrolln top
   var $frame = $('.select_frame[data-rel='+meteor_id+']');
   var scroll_to = parseInt(meteor_id);
   var height, factor;


   meteor_id = parseInt(meteor_id);

   // Cur has changed
   $('.select_frame').removeClass('cur');
   $frame.addClass('cur');
  
   // Add Image to Cropped selector
   $('#cropped_frame_selector').css('background-image','url('+img_path+')');

   // Add Image to Cropped selector
   $('#cropped_frame_selector').css('background-image','url('+img_path+')');

   // Get Height to init the UI (if needed)
   height = $('#select_meteor_modal').outerHeight() - $('#select_meteor_modal .modal-header').outerHeight() - $("#thumb_browwser").outerHeight() - $('#below_cfs').outerHeight();
   
   // 16/9 format
   $('#cropped_frame_selector').css('height',parseInt(height) - 30)
   $('#cropped_frame_selector').css('width', parseInt((parseInt(height)-30)*16/9));   
   
   // Update Title
   $('#sel_frame_id, .sel_frame_id').text(' - frame #' +  meteor_id);   
 
   // Scroll to frame -1 on top if it exists
   if($('.select_frame[data-rel="'+meteor_id+'"]').length==0) {
      $('#frame_select_mod').scrollTo($('.select_frame[data-rel=0]'), 150 );
   } else if($('.select_frame[data-rel="'+(scroll_to-4)+'"]').length>0) {
      $('#frame_select_mod').scrollTo($('.select_frame[data-rel="'+(scroll_to-4)+'"]'), 150 );
   } else {
      $('#frame_select_mod').scrollTo($('.select_frame[data-rel="'+(scroll_to )+'"]'), 150 ); 
   }
   
   factor  = w / $('#cropped_frame_selector').width();  // Same for W & H!!
 
   // Add circles on the selector
   add_all_circles(meteor_id,factor);

   // GO!
   select_meteor_pos(factor);


   /*

      if(all_frames_ids.indexOf(i) >= 0 ) { 
         // already updated?
         test_new_pos = get_new_pos(i);
          if(test_new_pos != false) {
             xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 

             add_debug('YY # ' + i + " => " + parseInt(xy[0]/factor) + " , " + parseInt(xy[1]/factor));


             addCircleRepair(xy[0]/factor,xy[1]/factor,i,'nb'); 
          } else {
            xy = convert_to_local(parseInt($('#fr_'+i).attr('data-org-x')),parseInt($('#fr_'+i).attr('data-org-y'))); 
            addCircleRepair(xy[0]/factor,xy[1]/factor,i,'b'); 
          }
      }
   } 
   */


   

   /*

   // Remove All Circles
  




   // Add Cur to image chooser
   $('.select_frame').removeClass('cur');
   $('.select_frame[data-rel="'+meteor_id+'"]').addClass('cur');

   // Scrolln top
   var $frame = $('.select_frame[data-rel='+meteor_id+']');
   var scroll_to = parseInt(meteor_id);

   // Cur has changed
   $('.select_frame').removeClass('cur');
   $frame.addClass('cur');

   // Not "done" yet
   $('#cropped_frame_selector').removeClass('done');

   // We load the image
   $('#cropped_frame_selector').css({
      'background-image':'url('+$($frame.find('img')).attr('src')+')'
   }); 

   

   // Add circles for 3 frames before and 3 frames after
   meteor_id = parseInt(meteor_id);

   // console.log("METEOR ID", meteor_id);


   
 


   // We get the 3 frames before if they exists
   if(all_frames_ids.indexOf((meteor_id-1))>=0) {
  
      for(var i = meteor_id-1; i >= meteor_id - 3 ; i--) {  
         if(all_frames_ids.indexOf(i) >= 0 ) { 
            // already updated?
            test_new_pos = get_new_pos(i);
             if(test_new_pos != false) {
                xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 

                add_debug('YY # ' + i + " => " + parseInt(xy[0]/factor) + " , " + parseInt(xy[1]/factor));


                addCircleRepair(xy[0]/factor,xy[1]/factor,i,'nb'); 
             } else {
               xy = convert_to_local(parseInt($('#fr_'+i).attr('data-org-x')),parseInt($('#fr_'+i).attr('data-org-y'))); 
               addCircleRepair(xy[0]/factor,xy[1]/factor,i,'b'); 
             }
         }
      } 
   }  

   // We get the 3 frames after if they exists
   if(all_frames_ids.indexOf((meteor_id+1))>=0) {
  
      for(var i = meteor_id+1; i <= meteor_id + 3 ; i++) { 
         
         if(all_frames_ids.indexOf(i) >= 0 ) { 

            // already updated?
            test_new_pos = get_new_pos(i);
            if(test_new_pos != false) {
               xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 
               add_debug('YY # ' + i + " => " + parseInt(xy[0]/factor) + " , " + parseInt(xy[1]/factor));

               addCircleRepair(xy[0]/factor,xy[1]/factor,i,'na'); 
            } else {
               xy = convert_to_local(parseInt($('#fr_'+i).attr('data-org-x')),parseInt($('#fr_'+i).attr('data-org-y'))); 
               addCircleRepair(xy[0]/factor,xy[1]/factor,i,'a'); 
            }
 
         }
      } 
   }     

   // Add Current Value 
   test_new_pos = get_new_pos(meteor_id);
   if(test_new_pos != false) {
      xy = convert_to_local(parseInt(test_new_pos[0]),parseInt(test_new_pos[1])); 
      addCircleRepair(xy[0]/factor,xy[1]/factor,meteor_id,'x'); 
   } else {
      xy = convert_to_local(parseInt($('#fr_'+meteor_id).attr('data-org-x')),parseInt($('#fr_'+meteor_id).attr('data-org-y'))); 
      addCircleRepair(xy[0]/factor,xy[1]/factor,meteor_id,'x'); 
   }

 
   // Select Meteor
   $("#cropped_frame_selector").unbind('click').click(function(e){
     
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;
 
      // Convert into HD_x & HD_y
      // from x,y
      var realX = relX*factor+x;
      var realY = relY*factor+y;
 
      // Transform values
      if(!$(this).hasClass('done')) {
          $(this).addClass('done');
      } else {
          $('#lh').css('top',relY);
          $('#lv').css('left',relX); 
      }
 
      cur_fr_id = $('#cropped_frame_select .cur').attr('data-rel');

      // Add current frame to frame_done if not already there
      if($.inArray(cur_fr_id, frames_done )==-1) {
         frames_done.push(parseInt(cur_fr_id));  // We push an int so we can get the min
         $('#fr_cnt').html(parseInt($('#fr_cnt').html())+1);
      }

      // Add info to frames_jobs
      frames_jobs.push({
         'fn': cur_fr_id,
         'x': Math.round(realX),
         'y': Math.round(realY)
      });
      
      // Add info to frame scroller
      $('#cropped_frame_select .cur').addClass('done').find('.pos').html('<br>x:' + parseInt(realX) + ' y:'  + parseInt(realY));
      
      // Go to next frame
      go_to_next(parseInt(cur_fr_id)+1,all_frames_ids);
      
  }).unbind('mousemove').mousemove(function(e) {
      
      var parentOffset = $(this).offset(); 
      var relX = e.pageX - parentOffset.left - select_border_size;
      var relY = e.pageY - parentOffset.top - select_border_size;

      // Cross
      if(!$(this).hasClass('done')) {
          $('#lh').css('top',relY-2);
          $('#lv').css('left',relX-2); 
      }

      add_mouse_pos(parseInt(relX*factor),parseInt(relY*factor),factor);

  });
 
 */
   return false;
 
}

 

// Open the Modal with a given meteor
function open_meteor_picker(meteor_id, img_path) {

   // Show Modal if necessary
   if($('#select_meteor_modal').hasClass('show')) { 
      add_frame_inside_meteor_select(img_path, meteor_id);
      $('#select_meteor_modal').css('padding-right',0);
      $('body').css('padding',0);
   } else {
      
      // When the modal already exists 
      $('#select_meteor_modal').on('shown.bs.modal', function () {
         add_frame_inside_meteor_select(img_path, meteor_id);
         $('#select_meteor_modal').css('padding-right',0);
         $('body').css('padding',0); // Because we don't want slidebars on body
      }).modal('show');

   }  

   // Click from Top of the modal
   $('.select_frame').unbind('click').click(function() {
      var $t = $(this);
      var img_path = $t.find('img').attr('src');
      $('#cropped_frame_selector').css('background-image','url(none)').css('border','2px solid #ffe52e');
      add_frame_inside_meteor_select(img_path,$t.attr('data-rel'));
   });
   return false; 
} 



/*******************************
 * MAIN SETUP
 **/

function setup_manual_reduc1(all_cropped_frames) { 
  
    // Only for loggedin
   if(test_logged_in()==null) { 
      return false;
   }
 
   // Add modal Template  
   addPickerModalTemplate(all_cropped_frames); 

   // We copy the original frames from the json 
   tmp_JSON_Frames = json_data['frames'];
   $.each(tmp_JSON_Frames, function(i,v) {
      tmp_JSON_Frames[i] = {'fn':v['fn'],'x':v['x'],'y':v['y']};
   });

   console.log(tmp_JSON_Frames);
   return false;
   
   // Click on a thumb in the reduc table
   $('.wi a').click(function(e) { 
      var $tr = $(this).closest('tr'); 
   
      // Get meteor id
      var meteor_id = $tr.attr('id');
      meteor_id = meteor_id.split('_')[1];
   
      open_meteor_picker(meteor_id,$tr.find('img').attr('src'));
      return false;
   });


   // Click on "Big" button 
   $('.reduc1').click(function(e) 
      { $('.wi a')[0].click();
   });


   /*


   // Click on "SEND TO API" (Yellow button) 
   $('#create_all').unbind('click').click(function() {
      var vtl = test_logged_in();
      var usr = getUserInfo();
      usr = usr.split('|');

      loading_button($(this)); 

      if($("#post_form").length==0) { 

         $('<form id="post_form" action="'+API_URL+'" method="post">\
            <input type="hidden" name="data" />\
            <input type="hidden" name="function" value="frames" />\
            <input type="hidden" name="tok" value="'+vtl+'" />\
            <input type="hidden" name="usr" value="'+usr[0]+'" />\
            <input type="hidden" name="st" value="'+stID+'"/>\
         </form>').appendTo($('body')); 
      }
 
      if(frames_jobs.length!=0) {

        
         // Add the cropped video path as a ref to the reduction 
         frames_jobs['det'] = cropped_video;
         
         // Update the temporary form and submit it (POST)
         $('#post_form input[name=data]').val(JSON.stringify(frames_jobs));

         // POST ASYNC 
         var formData = $("#post_form").serialize();
         var URL = $("#post_form").attr("action");
         $.post(URL,
            formData,
            function(data, textStatus, jqXHR)  {
               //data: Data from server.    
               // console.log("data from server ")
               // console.log(data);


            }).fail(function(jqXHR, textStatus, errorThrown) 
            {
               // console.log("FAIL")
            });
               
      } else {
         bootbox.alert({
            message: "Error: nothing to update!",
            className: 'rubberBand animated error',
            centerVertical: true 
         })
      }

      load_done_button($(this));  
   })
   */
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