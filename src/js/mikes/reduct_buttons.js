 


function show_hide_grid() {
    // How/ Hide Grid
    $('#show_grid').click(function() {
        var canvas = document.getElementById("c");
        var cntx= canvas.getContext("2d"); 
        if(typeof $(this).attr('data-src') == 'undefined') {
            cntx.drawImage(document.getElementById('half_stack_file'), 0, 0);
            cntx.globalAlpha = .2; 
            cntx.drawImage(document.getElementById('az_grid_file'), 0, 0);
            $(this).attr('data-src',1).find('span').text('Hide Grid');
        } else {
            cntx.globalAlpha = 1;
            cntx.drawImage( document.getElementById('half_stack_file'), 0, 0);
            $(this).removeAttr('data-src').find('span').text('Show Grid');
        }
    });
}


function show_hide_zoom() {
    $('#show_zoom').click(function() {
        if(typeof $(this).attr('data-src') == 'undefined') {
            $('.canvas_zoom_holder').removeAttr('hidden');
            $(this).attr('data-src',1).find('span').text('Hide Zoom');
        } else {
            $('.canvas_zoom_holder').attr('hidden','true'); 
            $(this).removeAttr('data-src').find('span').text('Show Zoom');
        }
    });
};


$(function() {

    show_hide_grid(); 
    show_hide_zoom();
})