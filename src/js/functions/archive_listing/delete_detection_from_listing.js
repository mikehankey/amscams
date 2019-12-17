// Update counter
function update_selected_counter() {
   $('.sel-ctn').text($('.preview.selected').length);
}

// Delete multiple MEteors
function reject_multiple_archived_meteor(array_of_jsid, ids) {

   
   bootbox.confirm("Are you sure you want to PERMANENTLY delete these detections?", function(result){ 

      if(result) {
         // Deleting
            $.each(ids, function(i,v){ 
               loading({text:"Deleting", container:$("#"+v), overlay:true, standalone:true});
         }); 

         $.ajax({ 
               type:"POST",
               url:  "webUI.py?cmd=delete_archive_multiple_detection",
               data: {detections: array_of_jsid},
               success: function(data) { 
                     $.each(ids, function(i,v){ 
                           meteor_is_deleted(v); 
                     });
                     
               }, 
               error: function() {
                     alert('Impossible to reject. Please, reload the page and try again later.')
                     loading_done();
               }
         });
      }  
   }
    
}

$(function() {

   // Select one from checkbox
   $('.sel-box input[type=checkbox]').change(function() {
       var $t = $(this), f = $t.attr('id'), id = f.substr(5,f.length);
       console.log("SELETECT ID " + id)
       if($t.is(':checked')) {
           $('#'+id).addClass('selected');
       } else {
           $('#'+id).removeClass('selected');
       }
        update_selected_counter();
    });


    // Select one from div
    $('.select-to').click(function(e) {
        if($(e.target).hasClass('select-to')) {
           e.stopImmediatePropagation();
           $(this).find('.sel-box input[type=checkbox]').click();
        }
    }) 
   
    // Select All
    $('#sel-all-archive').click(function() {
       $('.sel-box input[type=checkbox]').click();
       update_selected_counter();
    })

    // Delete All
    $('.del-all-archive').click(function() {
        // Get all id
    
        var detections = [];
        var ids = [];
        jQuery.each($('.preview.selected'), function( i, val ) { 
               detections.push($(val).find('.delete_meteor_archive_gallery').attr('data-meteor'));
               ids.push($(val).attr('id'));
           }
        );
 
        reject_multiple_archived_meteor(detections, ids);

        
    })
})



$(function() {

   var $sel = $('input[name=meteor_select]');
   if($sel.length!==0) {

       $sel.on('change',function() {
           var id = $(this).attr('id');
           loading({"text":"Selecting meteors..."});
           switch (id) {
               case "reduced":
                   // Reduced Only
                   $('.preview.norm').fadeOut();
                   $('.preview.reduced').fadeIn();
                   break;
               case "non_reduced":
                  // Reduced Only
                  $('.preview.norm').fadeIn();
                  $('.preview.reduced').fadeOut();
                  break;
               default:
                   $('.preview.norm').fadeIn();
           }
           loading_done();
        });


   }
})