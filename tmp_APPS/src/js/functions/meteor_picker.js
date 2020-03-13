
function setup_select_meteor(anti_cache=-1) {
   var viewer_dim = 500;
   var all_frames_ids = [];
 

   // Get all the frame ids
   $('#reduc-tab table tbody tr').each(function() {
       var id = $(this).attr('id');
       id = id.split('_');
       all_frames_ids.push(parseInt(id[1]));
   });
 

   // Click on selector (thumb)
   $('.wi a').click(function() {
 
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
       var neighbor = get_neighbor_frames(meteor_id); 

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
       if(anti_cache!=1 && anti_cache==meteor_id) {
           $('.meteor_chooser').css('background-image','url('+$img.attr('src')+'&d='+ Math.round(Math.random(10000)*10000)+')').css('border','2px solid ' + color);
       } else {
           $('.meteor_chooser').css('background-image','url('+$img.attr('src')+')').css('border','2px solid ' + color);
       }
       
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

       

   });
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


// Actions on modal 
function setup_modal_actions(fn_id,x,y) {
    
   // Warning: preview  = 500x500
   //    thumb real dim = 50x50
   var thumb_prev = 500;
   var thumb_dim  = 50;
   var factor = 500/50;

   x = parseInt(x);
   y = parseInt(y);

   // Update Info
   $('#meteor_org_pos').html('<b>Org:</b> x:'+x+'/y:'+y);
   $('#meteor_pos').text('x:'+x+'/y:'+y);

   // Remove Helper
   $('.cross_holder.next, .cross_holder.prev').remove();

   // Add Next Help Point 
   var nextH = get_help_pos('next',parseInt(fn_id));
    
   if(nextH && typeof nextH !== 'undefined'  ) { 
       if( nextH.x !== null && typeof  nextH.x !== null) {
             // 225 for circle diameter
           var rX = (225+(nextH.x-x)*factor);
           var rY = (225+(nextH.y-y)*factor);
           $('<div class="cross_holder next" style="top:'+rY+'px; left:'+rX+'px"><div class="cross" style="border:1px solid '+nextH.color+'"></div></div>').appendTo('.meteor_chooser');
       }
   }
   nextH = get_help_pos('prev',parseInt(fn_id));
   if(nextH && typeof nextH !== 'undefined' ) { 
       if( nextH.x !== null && typeof  nextH.x !== null) {
           // 225 for circle diameter
           var rX = (225+(nextH.x-x)*factor);
           var rY = (225+(nextH.y-y)*factor);
           $('<div class="cross_holder prev" style="top:'+rY+'px; left:'+rX+'px"><div class="cross" style="border:1px solid '+nextH.color+'"></div></div>').appendTo('.meteor_chooser');
       }
   }
    

   $(".meteor_chooser").unbind('click').click(function(e){
       var parentOffset = $(this).offset(); 
       var relX = parseFloat(e.pageX - parentOffset.left);
       var relY = parseFloat(e.pageY - parentOffset.top);

       //WARNING ONLY WORKS WITH SQUARES
       var realX = relX/factor+x-thumb_dim/2;
       var realY = relY/factor+y-thumb_dim/2;

       // Transform values
       if(!$(this).hasClass('done')) {
           $(this).addClass('done');
       } else {
           $('#lh').css('top',relY);
           $('#lv').css('left',relX);
           $('#meteor_pos').text("x:"+parseInt(realX)+'/y:'+parseInt(realY));
       }
        
       select_meteor_ajax(fn_id,realX,realY);

   }).unbind('mousemove').mousemove(function(e) {
       
       var parentOffset = $(this).offset(); 
       var relX = e.pageX - parentOffset.left;
       var relY = e.pageY - parentOffset.top;

       //WARNING ONLY WORKS WITH SQUARES
       var realX = relX/factor+x-thumb_dim/2;
       var realY = relY/factor+y-thumb_dim/2;

       // Cross
       if(!$(this).hasClass('done')) {
           $('#lh').css('top',relY-2);
           $('#lv').css('left',relX-2);
           $('#meteor_pos').text("x:"+parseInt(realX)+'/y:'+parseInt(realY));
       }
   });
}



// Modal for selector
function addModalTemplate(meteor_id,neighbor) {
   var c; 
   if($('#select_meteor_modal').length==0) {

       c = '<div id="select_meteor_modal" class="modal fade multiple-select" tabindex="-1">\
       <input type="hidden" name="thumb_w"/><input type="hidden" name="thumb_h"/>\
       <div class="modal-dialog  modal-lg modal-dialog-centered" role="document">\
       <div class="modal-content">\
       <div class="modal-header"> \
           <div><strong>FRAME #<span id="sel_frame_id"></span></strong> \
           - Click the center of the meteor to update the reduction frame. \
           </div>\
           <div>\
                   <button id="switch_select_mode" class="btn btn-primary btn-sm" data-lbl="Switch to multiple mode"><b>Switch to single mode</b></button>\
           </div>\
       </div>\
       <div class="modal-body">\
       <div class="select_meteor_holder">\
           <button id="met-sel-next" title="Next" type="button" class="mfp-arrow mfp-arrow-right mfp-prevent-close"></button>\
           <button id="met-sel-prev" title="Prev" type="button" class="mfp-arrow mfp-arrow-left mfp-prevent-close"></button>\
           <div class="d-flex justify-content-center" id="nav_prev">\
           </div><div style="box-shadow: 0 0px 8px rgba(0,0,0,.6);" class="meteor_chooser">\
           <div id="org_lh"></div><div id="org_lv"></div><div id="lh"></div><div id="lv"></div></div>\
               <div class="d-flex justify-content-between mt-2" style="max-width: 500px;margin: 0 auto;">\
                   <div><a class="btn btn-danger delete_frame_from_modal"><i class="icon-delete"></i> Delete the frame #<span class="sel_frame_id"></span></a></div>\
                   <div class="select_info"> \
                       <span id="meteor_org_pos"><b>Org:</b></span><br/>\
                       <span id="meteor_pos"></span> \
                   </div> \
           </div>\
           </div>\
           <div class="update_meteor_thumb_pos_list">\
               <div class="d-flex align-items-start flex-column update_meteor_thumb_pos_list_ins">\
                   <h5>List of updates</h5>\
                   <div class="meteor_thumb_pos_list"></div>\
                   <div class="mt-auto"><button id="select_multiple_meteors_ajax" class="btn btn-primary">Apply all updates</button></div>\
               </div>\
           </div>\
       </div>\
       <div class="modal-footer bd-t mt-3 pt-2 pb-2 pr-2">\
       <button type="button" hidden>Save</button>\
       <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>\
       </div></div></div>';
       $(c).appendTo('body');
   }  


   // We update the preview
   $('#nav_prev').html(''); 


   // Add the "create frames buttons"
   $.each(neighbor, function(i,v)  {
       if(v.id==meteor_id) {
           _hclass = 'ccur';
           _class = 'prev-th cur';
       } else {
           _hclass = '';
           _class = 'prev-th ';
       } 

       if(v.id==0) { 


           _status = ""
           /*
           if(multiple_select) {
               _status = "hidden"
           }
           */

           // We add a +
           $('<div class="add_fr_btn">\
               <a title="Add a frame" ' + _status + ' class="create_frame_fs btn btn-primary prev-th" data-rel="'+v.id+'" data-fr="'+v.vid+'"><i class="icon-plus display-block"></i> #'+v.vid+'</a>\
               </div>').appendTo($('#nav_prev'));

       } else {
           $('<div class="'+_hclass+'"><a class="select_frame select_frame_btn" data-m="'+v.id+'"><img src="'+v.img+'" id="'+v.id+'" style="border-color:'+v.color+';" class="'+_class+'" ><span>#'+v.id+'</span></a></div>').appendTo($('#nav_prev'));
       }

   });


  
   // Click on thumbs
   $('.select_frame').unbind('click').click(function() {
       $('tr#fr_'+$(this).attr('data-m') + ' .select_meteor').click();
   })

   // Click on delete 
   $('.delete_frame_from_modal').unbind('click').click(function() {
       delete_frame_from_crop_modal(parseInt($('#sel_frame_id').html()));
   });

   // Click on "+"
   $('.create_frame_fs').click(function() { 
       get_frame($(this).attr('data-fr'));
   }); 
   
   // Switch  "Multiple Mode" / "Single Mode"
   $('#switch_select_mode').click(function(e) { 
       e.stopImmediatePropagation();
       var t, $t = $(this);
       multiple_select = (multiple_select==true)?false:true;
       t = $t.text();
       $t.text($t.attr('data-lbl')).attr('data-lbl', t);
       $('#select_meteor_modal').toggleClass('multiple-select');

       /* Hide + frames on multiple mode ?
       if(multiple_select == true) {
           $('.create_frame_fs').attr('hidden','true');
           meteor_select_updates = []; // We reset the values
       } else {
           $('.create_frame_fs').removeAttr('hidden');
       }
       */
       return false;
   })



    
   // Update Multiple 
   $('#select_multiple_meteors_ajax').click(function(e){
       e.stopImmediatePropagation();
       select_multiple_meteors_ajax();
       return false;
   });

   update_meteor_info_list(meteor_id);



  
}