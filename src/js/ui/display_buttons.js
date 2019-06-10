 var has_grid;


function show_hide_grid() {
    
    // Test if we have a grid
    if(!has_grid) {
        if(typeof az_grid_file  == 'undefined'){
            has_grid = false;
        } else {
            has_grid = !($.trim(az_grid_file) === "");
        }
    }
     
        // How/ Hide Grid
        $('#show_grid').click(function() {

            if(has_grid) {

                var canvas = document.getElementById("c");
                var cntx= canvas.getContext("2d"); 
                if(!$('#c').hasClass('grid')) {
                    cntx.drawImage(document.getElementById('half_stack_file'), 0, 0);
                    cntx.globalAlpha = .2; 
                    cntx.drawImage(document.getElementById('az_grid_file'), 0, 0);
                    $(this).find('span').text('Hide Grid');
                    $('#c').addClass('grid');

                    if($('#c').hasClass('zoom')) {
                        $('#show_zoom').click();
                    }

                } else {
                    cntx.globalAlpha = 1;
                    cntx.drawImage( document.getElementById('half_stack_file'), 0, 0);
                    $('#c').removeClass('grid');
                    $(this).find('span').text('Show Grid');
                }

            } else {
                bootbox.alert({
                    message: "The Grid is missing for this meteor.",
                    className: 'rubberBand animated error',
                    centerVertical: true
                });
            }
       
        });
   
}


function show_hide_zoom() {
    $('#show_zoom').click(function() {
        if(!$('#c').hasClass('zoom')) {
            $('.canvas_zoom_holder').slideDown();
            $(this).find('span').text('Hide Zoom');
            $('#c').addClass('zoom');

            if($('#c').hasClass('grid')) {
                $('#show_grid').click();
            }

        } else {
            $('.canvas_zoom_holder').slideUp();
            $('#c').removeClass('zoom');
            $(this).find('span').text('Show Zoom');
        }
    });
};


$(function() {
    
    if($('#c').length!=0) {
        show_hide_grid(); 
        show_hide_zoom();
    }
})