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
      /*
      if(typeof v['dist_from_last'] !='undefined') {
         if(parseFloat(v['dist_from_last'])>parseFloat(med_dist*parseInt($('#error_factor_dist_len').val()))) {
            dist_err = '<td style="color:#f00">'+v['dist_from_last'].toFixed(2)+'</td>';
         } else {
            dist_err = '<td>'+v['dist_from_last'].toFixed(2)+'</td>';
         }
      } else {
         
      }
      */
      dist_err = '<td>?</td>';
      
      

      if(typeof v['intensity']!=='undefined') {
         intensity = '<td>'+v['intensity']+'</td>'
      } else {
         intensity = '<td>?</td>';
      }


        // Thumb	#	Time	X/Y - W/H	Max PX	RA/DEC	AZ/EL 
        table_tbody_html+= '<tr id="fr_'+frame_id+'" data-fn="'+frame_id+'" data-org-x="'+v['x']+'" data-org-y="'+v['y']+'">'
        table_tbody_html+= '<td id="thb_'+frame_id+'" class="wi" data-src="'+all_colors[i]+'"><a class="img_link" href=""><img src="/APPS/dist/img/loader.svg" style="width:80px;height:auto"></a></td>';
        table_tbody_html+= '<td>'+frame_id+'</td><td>'+_time[1]+'</td><td>'+v['ra'].toFixed(PRECISION)+'&deg;&nbsp;/&nbsp;'+v['dec'].toFixed(PRECISION)+'&deg;</td><td>'+v["az"].toFixed(PRECISION)+'&deg;&nbsp;/&nbsp;'+v["el"].toFixed(PRECISION)+'&deg;</td><td>'+ parseFloat(v['x']) +'&nbsp;/&nbsp;'+parseFloat(v['y'])  +'</td><td>'+ v['w']+'x'+v['h']+'</td>';
       

        if( i==middle_frame_index) {
            middle_frame = thumb_path;
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
    //$("#play_anim").css('background','url('+middle_frame+')'),

    // Setup  Range for red transparency on canvas
    $('input[name=frame_transp]').change(function(e) { 
      change_red_canvas_transp(parseInt($(this).val()), canvas);
    })
}


// Change Transparency of Reduction elements on canvas
function change_red_canvas_transp(trans,canvas) {
   var objects = canvas.getObjects();
   trans = trans / 100;
    $.each(objects,function(i,v){
        if(v.type=='reduc_rect') {
            v.set({
               opacity: trans
           });
        }
    });
    canvas.renderAll();
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
 