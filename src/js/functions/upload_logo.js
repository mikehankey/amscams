// Auto Submit when a file is selected 
$('#logo_file_upload').change(function() {
    $('#upload_logo').submit();
})


$("form#upload_logo").submit(function(e) {
    e.preventDefault();    
    var formData = new FormData(this);
    loading({text:'Uploading your image',overlay:true})
    $.ajax({
        url: '/pycgi/webUI.py?cmd=upload_logo',
        type: 'POST',
        data: formData,
        success: function (data) {
            alert(data)
            loading_done();
        },
        cache: false,
        contentType: false,
        processData: false
    });
});