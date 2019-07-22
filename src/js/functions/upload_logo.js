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
            
            loading_done();
            if(typeof data.error == 'undefined') {
                bootbox.alert({
                    message: "Your image has been uploaded. We will now reload this page",
                    className: 'rubberBand animated',
                    centerVertical: true,
                    callback: function() {
                        location.reload();
                    }
                });
            } else {
                bootbox.alert({
                    message: "We cannot upload your image. Please, try again later.",
                    className: 'rubberBand animated error',
                    centerVertical: true 
                });
            }
                
        },
        cache: false,
        contentType: false,
        processData: false
    });
});