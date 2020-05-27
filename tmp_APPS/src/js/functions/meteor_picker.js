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



// Test if a frame is on the json and return the related data
function get_data_from_json(frame_id) {
   
   for(var i=0; i< tmp_JSON_Frames.length; i++) {
      if(tmp_JSON_Frames[i]['fn']==frame_id) {
         return {'x': tmp_JSON_Frames[i]['x'], 'y':  tmp_JSON_Frames[i]['y']}
      }
   } 
   return false;
}



// Delete a frame from the json 
// Warning: it's temporary as we don't save it 
// It is used to show the circles that correspond to the 
// data that will be send to the API
function delete_frame_from_json(frame_id) {
 
   for(var i=0; i< tmp_JSON_Frames.length; i++) {
      if(tmp_JSON_Frames[i]['fn']==frame_id) {
         tmp_JSON_Frames.splice(i, 1);
         break;
      }
   }   
}


// Get min/max frame id from Tmp JSON
function get_min_max_from_json() {
   var arFn = [];
   
   for(var i=0; i< tmp_JSON_Frames.length; i++) {
      arFn.push(tmp_JSON_Frames[i]['fn']); 
   }   

   return {'min':Math.min.apply(Math,arFn), 'max':Math.max.apply(Math,arFn)};
}


// Update or add a frame to  update_tmp_JSON_frames
function  update_tmp_JSON_frames(data) {
   var updated = false;

   // Is the frame already exists in tmp_JSON_Frames(?)
   for(var i=0; i< tmp_JSON_Frames.length; i++) {
      if(tmp_JSON_Frames[i]['fn']== data['fn']) {
         tmp_JSON_Frames[i]['x'] = data['x'];
         tmp_JSON_Frames[i]['y'] = data['y'];
         updated = true;
         break;
      } 
   }   

   if(!updated) {
      tmp_JSON_Frames.push(data);
   }


} 


 

   /*


   // Click on "SEND TO API" (Yellow button) 
   $('#create_all').unbind('click').click(function() {
      var vtl = test_logged_in();
      var usr = getUserInfo();
      usr = usr.split('|');

     
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
 
   })
   */