$(function() {
    $('.delete_video').click(function(e){
        var $t = $(this);
        e.stopImmediatePropagation();

        bootbox.confirm({
            message: "Are you sure you want to permanently delete this video?",
            buttons: {
                confirm: {
                    label: 'Yes',
                    className: 'btn-success'
                },
                cancel: {
                    label: 'No',
                    className: 'btn-danger'
                }
            },
            className: 'rubberBand animated',
            centerVertical: true,
            callback: function (result) {
                if(result==1) {
                   loading({text: "Deleting Video",overlay:true});

                    $.ajax({ 
                        url:  "/pycgi/webUI.py",
                        data: {
                            cmd: "delete_custom_video",
                            vid: $t.attr('data-rel')
                        },
                        success: function(data) {
                            $t.closest('.preview').remove();
                        }, 
                        error: function(e) {
                            window.location.reload();
                        }
                    });
                }
            }
        });
    }) 
});