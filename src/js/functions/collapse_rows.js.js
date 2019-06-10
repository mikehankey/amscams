$(function() {
    $('.toggler').click(function() {
        var tar = $(this).attr('data-tog');
        $('#'+tar).toggleClass('show');
    });
    
})