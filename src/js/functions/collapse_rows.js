$(function() {
    $('.toggler').click(function() { 
        $($(this).attr('data-tog')).toggleClass('show');
    });
    
})