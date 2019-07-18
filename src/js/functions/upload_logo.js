// Auto Submit when a file is selected 
$('#logo_file_upload').change(function() {
    $('#upload_logo').submit();
})


$("form#upload_logo").submit(function(e) {
    e.preventDefault();    
    var formData = new FormData(this);

    $.ajax({
        url: '/pycgi/webUI.py?cmd=upload_logo',
        type: 'POST',
        data: formData,
        success: function (data) {
            alert(data)
        },
        cache: false,
        contentType: false,
        processData: false
    });
});