$('.sel-box input[type=checkbox]').change(function() {
    var $t = $(this), f = $t.attr('for'), id = f.substr(5,f.length);
    if($t.is(':checked')) {
        $('#'+id).addClass('selected');
    } else {
        $('#'+id).removeClass('selected');
    }
 
 });