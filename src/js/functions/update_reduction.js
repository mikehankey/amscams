function update_reduction_on_canvas_and_table(json_resp) {
    var smf = json_resp['meteor_frame_data'];

    if(typeof smf == 'undefined') {
        smf = json_resp['sd_meteor_frame_data'];
    }

    var lc = 0;
    var table_tbody_html = '';
    var rad = 6;

    $.each(smf, function(i,v){
        
        // Get thumb path
        var frame_id = v[1];
        var thumb_path = my_image.substring(0,my_image.indexOf('-half')) + '-frm' + frame_id + '.png';
        var square_size = 6;

        // Thumb	#	Time	X/Y - W/H	Max PX	RA/DEC	AZ/EL
        table_tbody_html+= '<tr><td><img alt="Thumb #'+frame_id+'" src='+thumb_path+' width=50 height=50 class="img-fluid select_meteor"/></td>';
        table_tbody_html+= '<td>'+frame_id+'</td><td>'+v[0]+'</td> <td>'+ (v[2]/2)+'/'+parseFloat(v[3]/2)+'</td><td>'+v[4]+'</td><td>'+v[5]+'</td>';
        table_tbody_html+= '<td>'+v[6]+'</td><td>'+v[7]+'/'+v[8]+'</td><td>'+v[9]+'/'+v[10]+'</td>'
        table_tbody_html+= '<td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>';
        table_tbody_html+= '<td><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>';

        // Add Rectangle
        canvas.add(new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.5)', 
            left:  v[2]/2-rad, 
            top:   v[3]/2-rad,
            width: 10,
            height: 10 ,
            selectable: false,
            type: 'reduc_rect'
        }));

    });

    // Replace current table content
    $('#reduc-tab tbody').html(table_tbody_html);
}