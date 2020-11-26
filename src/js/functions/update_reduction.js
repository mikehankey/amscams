function update_reduction_on_canvas_and_table(json_resp) {
    var smf = json_resp['meteor_frame_data'];

    if(typeof smf == 'undefined') {
        smf = json_resp['sd_meteor_frame_data'];
    }

    var lc = 0;
    var table_tbody_html = '';
    var rad = 6;


    var all_frame_ids = [];

    // Get all the frame IDs so we know which one are missing
    $.each(smf, function(i,v){
        all_frame_ids.push(parseInt(v[1]));
    });
    // Create Colors
    var rainbow = new Rainbow();
    rainbow.setNumberRange(0, 255);
    var all_colors = [];
    var total = all_frame_ids.length; 
    var step = parseInt(255/total); 
    for (var i = 0; i <= 255; i = i + step) {
        all_colors.push('#'+rainbow.colourAt(i));
    }
     
    
    $.each(smf, function(i,v){
 
        
        // Get thumb path
        var frame_id = parseInt(v[1]);
        id_pad = v[1]
        id_str = id_pad.toString()
        if (id_str.length == 1) {
           pid = "000" + id_str
        }
        if (id_str.length == 2) {
           pid = "00" + id_str
        }
        if (id_str.length == 3) {
           pid = "0" + id_str
        }
        if (id_str.length == 4) {
           pid = id_str
        }
        var thumb_path = my_image.substring(0,my_image.indexOf('-half')) //+ '-frm' + frame_id + '.png';
        var file_parts = thumb_path.split("/")
        frame_fn = file_parts[5]
        frame_date = file_parts[4]
        date_el = frame_date.split("_")
        frame_year = date_el[0]
        frame_month = date_el[1] 
        frame_day = date_el[2]
        var thumb_path = "/mnt/ams2/CACHE/" + frame_year + "/" + frame_month + "/" + frame_fn + "/" + frame_fn + "-frm" + pid + ".jpg"

        console.log("IPAD:", pid, thumb_path)
       
        var square_size = 6;
        var _time = v[0].split(' ');
  
        // Thumb	#	Time	X/Y - W/H	Max PX	RA/DEC	AZ/EL 
        table_tbody_html+= '<tr id="fr_'+frame_id+'" data-org-x="'+v[2]+'" data-org-y="'+v[3]+'"><td><div class="st" hidden style="background-color:'+all_colors[i]+'"></div></td>'
        table_tbody_html+= '<td><img alt="Thumb #'+frame_id+'" src='+thumb_path+'?c='+Math.random()+' width="50" height="50" class="img-fluid smi select_meteor" style="border-color:'+all_colors[i]+'"/></td>';
        table_tbody_html+= '<td>'+frame_id+'</td><td>'+_time[1]+'</td><td>'+v[7]+'&deg;/'+v[8]+'&deg;</td><td>'+v[9]+'&deg;/'+v[10]+'&deg;</td><td>'+ parseFloat(v[2])+'/'+parseFloat(v[3]) +'</td><td>'+ v[4]+'x'+v[5]+'</td>';
        table_tbody_html+= '<td>'+v[6]+'</td>';
        table_tbody_html+= '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';

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
            left:  v[2]/2-rad, 
            top:   v[3]/2-rad,
            width: 10,
            height: 10 ,
            selectable: false,
            type: 'reduc_rect',
            id: 'fr_' + frame_id
        }));

    });

    // Replace current table content
    $('#reduc-tab tbody').html(table_tbody_html);

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
        video_file:       main_vid,          // Defined on the page 
        cmd: 'update_red_info_ajax'
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
                setup_add_frames();
 
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

}
function test_missing_thumb_old() {
    var rows_with_missing_thumbs = [];
    var we_try_how_many_times = 10;
    var cnt = 0;
    $('#reduc-tab table img').each(function() {

        // 50 = normal size => 48 without border
	    if($(this).width()>49) {
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
