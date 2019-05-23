

    $(function() {
        $.contextMenu({
            selector: '.context-menu-one',
            callback: function(key, options) {
                alert("YO")
                id = options.$trigger.attr("id");
                var m = "clicked: " + key + id;
                if (key == 'reject') {
                   new_id = 'fig_' + id
                   $('#' + new_id).remove();
                   ajax_url = "webUI.py?cmd=override_detect&jsid=" + id
                   $.get(ajax_url, function(data) {
                      $(".result").html(data);
                   });
                }

                if (key == 'examine') {
                   window.location.href='webUI.py?cmd=examine&jsid=' + id
                   //alert("EXAMINE:")
                }
                if (key == 'play') {
                   //window.location.href='webUI.py?cmd=play_vid&jsid=' + id
                      $('#ex1').modal();
                      var year = id.substring(0,4);
                      var mon = id.substring(4,6);
                      var day = id.substring(6,8);
                      var hour = id.substring(8,10);
                      var min = id.substring(10,12);
                      var sec = id.substring(12,14);
                      var msec = id.substring(14,17);
                      var cam = id.substring(17,23);
                      var trim = id.substring(24,id.length);
                      var src_url = "/mnt/ams2/meteors/" + year + "_" + mon + "_" + day + "/" + year + "_" + mon + "_" + day + "_" + hour + "_" + min + "_" + sec + "_" + msec + "_" + cam + "-" + trim + ".mp4"
                      $('#v1').attr("src", src_url);

                }
                //window.console && console.log(m) || alert(m);
            },
            items: {
                "examine": {name: "Examine"},
                "play": {name: "Play Video"},
                "reject": {name: "Reject Meteor"}
                }
        });

        $('.context-menu-one').on('click', function(e){
            console.log('clicked', this);
        })
    });

      var last_x = 0
      var last_y = 0
      document.onmousemove = function(e) {
         last_x = e.pageX
         last_y = e.pageY
      }

      //$(this).on('mousemove', function(event) {
      //   var x = event.movementX
      //   var y = event.movementY
      //   if (event.keyCode == 120) {
            //   elementMouseIsOver = document.elementFromPoint(x,y)
      //    }
      //      console.log(x)
            //alert(event.keyCode)
       //})
      $(this).on('keypress', function(event) {
          emo = document.elementFromPoint(last_x,last_y).id
          new_id = 'fig_' + emo
          new_id = new_id.replace("_img", "")
          console.log("delete " + last_x + " " + last_y + " " + new_id)
          $('#' + new_id).remove();
          pid = new_id.replace("fig_", "")
          ajax_url = "webUI.py?cmd=override_detect&jsid=" + pid
          console.log(ajax_url)
          $.get(ajax_url, function(data) {
          $(".result").html(data);

          });



       })

