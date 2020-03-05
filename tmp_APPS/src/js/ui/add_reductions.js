function update_reduction_on_canvas_and_table(json_resp, canvas) {

   if(typeof json_resp== 'undefined' || typeof json_resp['frames'] == 'undefined') {
      return false;
   }
 
   var smf = json_resp['frames'];
    var PRECISION = 2;
 
    var lc = 0;
    var table_tbody_html = '';
    var rad = 6;


    var all_frame_ids = [];
 

    // If we have a "point_score", we update the value on the page
    if(json_resp['point_score'])  {
      if(parseFloat(json_resp['point_score'])>=3) {
         score = "<b style='color:#ff0000'>" + json_resp['point_score'] + "</b>"
      } else {
         score = json_resp['point_score'];
      }
      $('#point_score_val').html(score);
     
  
    }
     

   
    // Get all the frame IDs so we know which one are missing
    $.each(smf, function(i,v){
        all_frame_ids.push(parseInt(v[1]));
    });


    // Create Colors
    var rainbow = new Rainbow();
    rainbow.setNumberRange(0, 255);

    var all_colors = [];
    var total = all_frame_ids.length; 
    var step = 1;

    if(total>=255) {   
      // Default color for the end...
      for (var i = 255; i <= total; i = i + step) {
         all_colors[i] = '#0000ff';
      }
      for (var i = 0; i <= 255; i = i + step) {
         all_colors[i] = '#'+rainbow.colourAt(i);
      }
    } else {
      step = parseInt(255/total);  
      for (var i = 0; i <= 255; i = i + step) {
         all_colors.push('#'+rainbow.colourAt(i));
      }
    }
     

   
 
    // We need the "middle" frame to illustrate the thumb anim button
    var middle_frame = "";
    var middle_frame_index = 0
    if(typeof smf !== 'undefined' && smf.length>2) {
      middle_frame_index = parseInt(smf.length/2);
    } else {
      middle_frame_index = smf.length-1;
    }
      
    $.each(smf, function(i,v){
  
      // Get thumb path
      var frame_id = parseInt(v['fn']);
      var thumb_path = v['path_to_frame'] +'?c='+Math.random();
      var square_size = 6;
      var _time = v['dt'].split(' ');

      // Add the medium dist value
      // med_dist is defined on the page 
      if(typeof v['dist_from_last'] !='undefined') {
         if(parseFloat(v['dist_from_last'])>parseFloat(med_dist*parseInt($('#error_factor_dist_len').val()))) {
            dist_err = '<td style="color:#f00">'+v['dist_from_last'].toFixed(2)+'</td>';
         } else {
            dist_err = '<td>'+v['dist_from_last'].toFixed(2)+'</td>';
         }
      } else {
         dist_err = '<td>?</td>';
      }
      
      

      if(typeof v['intensity']!=='undefined') {
         intensity = '<td>'+v['intensity']+'</td>'
      } else {
         intensity = '<td>?</td>';
      }


        // Thumb	#	Time	X/Y - W/H	Max PX	RA/DEC	AZ/EL 
        table_tbody_html+= '<tr id="fr_'+frame_id+'" data-fn="'+frame_id+'" data-org-x="'+v['x']+'" data-org-y="'+v['y']+'"><td><div class="st" hidden style="background-color:'+all_colors[i]+'"></div></td>'
        table_tbody_html+= '<td><img alt="Thumb #'+frame_id+'" src='+thumb_path+' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:'+all_colors[i]+'"/></td>';
        table_tbody_html+= '<td>'+frame_id+'</td><td>'+_time[1]+'</td><td>'+v['ra'].toFixed(PRECISION)+'&deg;&nbsp;/&nbsp;'+v['dec'].toFixed(PRECISION)+'&deg;</td><td>'+v["az"].toFixed(PRECISION)+'&deg;&nbsp;/&nbsp;'+v["el"].toFixed(PRECISION)+'&deg;</td><td>'+ parseFloat(v['x']) +'&nbsp;/&nbsp;'+parseFloat(v['y'])  +'</td><td>'+ v['w']+'x'+v['h']+'</td>';
        table_tbody_html+= intensity;
        table_tbody_html+= dist_err;
        table_tbody_html+= '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';

        if( i==middle_frame_index) {
            middle_frame = thumb_path;
        }

        if(i==0) {
            // <a title="Add a frame" class="btn btn-primary btn-sm btn-mm add_f" data-rel="'+ (frame_id-1) +'"><i class="icon-plus"></i></a>
            // We add a "+" before and after on if necessary
            table_tbody_html+= '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a>';

            /*
            if(all_frame_ids.indexOf((frame_id+1))==-1) {
                table_tbody_html+= '<a class="btn btn-primary btn-sm btn-pp add_f" title="Add a frame" data-rel="'+ (frame_id+1) +'"><i class="icon-plus"></i></a></td>';
            } 
            */

            table_tbody_html+= '</td>';

        } else {
            // We add a "+" after only if we don't have the next frame in all_frame_ids
            /*
            if(all_frame_ids.indexOf((frame_id+1))==-1) {
                table_tbody_html+= '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a><a title="Add a frame" class="btn btn-primary btn-sm btn-pp add_f" data-rel="'+ (frame_id+1) +'"><i class="icon-plus"></i></a></td>';
            } else {
                */
                table_tbody_html+= '<td class="position-relative"><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>';
            //}
        }
    

        // Add Rectangle on canvas
        canvas.add(new fabric.Rect({
            fill: 'rgba(0,0,0,0)', 
            strokeWidth: 1, 
            stroke: all_colors[i], //'rgba(230,100,200,.5)', 
            left:  v['x']/2-rad, 
            top:   v['y']/2-rad,
            width: 10,
            height: 10 ,
            selectable: false,
            type: 'reduc_rect',
            id: 'fr_' + frame_id
        }));

    });

    // Replace current table content
    $('#reduc-tab tbody').html(table_tbody_html);

    // Replace Thumb used for the Anim Thumbs Preview
    $("#play_anim").css('background','url('+middle_frame+')'),

    // Reload the actions
    reduction_table_actions();
}


// Remove Reductions data from the canvas
function remove_reduction_objects_from_canvas() {
    var objects = canvas.getObjects()
    $.each(objects,function(i,v){
        if(v.type=='reduc_rect') {
            canvas.remove(objects[i]);
        }
    });
     
 }

function update_reduction_only(callback='') {
    var cmd_data = {
      json_file: json_file,          // Defined on the page 
      cmd: 'get_reduction_info'
    }

    loading({text:'Updating  reduction data...', overlay:true}); 
    
    $.ajax({ 
        url:  "/pycgi/webUI.py",
        data: cmd_data,
        success: function(data) {
        
            var json_resp = $.parseJSON(data); 

            if(json_resp['status']!==0) {
             
                // Remove All objects from Canvas with type =   type: 'reduc_rect'
                remove_reduction_objects_from_canvas();
                 
                // Update Reduction
                update_reduction_on_canvas_and_table(json_resp);
                
                // Update Add frames
                // setup_add_frames();
 
            }

            reduction_table_actions();
            
            if(callback!='') {
              callback();
            }

            loading_done();
 
        }, error: function(data) {
            
            loading_done();
            bootbox.alert({
                message: "Something went wrong with the reduction data. Please, try again later",
                className: 'rubberBand animated error',
                centerVertical: true 
            });
        }
    });
}



// test if we have a missing thumb 
function test_missing_thumb() {
    var rows_with_missing_thumbs = [];
    var we_try_how_many_times = 10;
    var cnt = 0;


   
    $('#reduc-tab table img').each(function() {

        // 50 = normal size => +47 without border
	    if($(this).width()<47) {
            rows_with_missing_thumbs.push($(this).closest('tr').attr('id'));
            // Replace with loading
            $(this).attr('data-src',$(this).attr('src')).attr('src','/pycgi/dist/img/anim_logo.svg');
        }
    
    });

    if(rows_with_missing_thumbs.length!=0) {
        // We try to load it  
        try_again = setInterval(function(){ 
            
            if(rows_with_missing_thumbs.length==0 || cnt>=we_try_how_many_times) {
                // Replace with processing
                clearInterval(try_again);

                $.each(rows_with_missing_thumbs, function(i,v) {
                    $('tr#'+v).find('img.select_meteor').removeAttr('data-src').attr('src','./dist/img/proccessing-sm.png');
                });
            }    

            $.each(rows_with_missing_thumbs, function(i,v) {
                var img_to_test = '/pycgi/' + $('tr#'+v).find('img.select_meteor').attr('data-src');
                //console.log('TEST ', img_to_test);
                $.ajax({
                    url:img_to_test,
                    type:'HEAD',
                    success:function(e){
                        // We place the image
                        $('tr#'+v).find('img.select_meteor').attr('src','data-src').removeAttr('data-src');
                        // We remove the td# from the array
                        rows_with_missing_thumbs.splice(i, 1);
                    },  
                    error:function() { // :( 
                    }
                });
            });

            cnt++;
        
        }, 3000);
    }
    
}


 