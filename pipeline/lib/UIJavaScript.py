"""

Java script functions for the UI

"""

JS_SHOW_HIDE = """
   <script>
   function show_hide(div_id) {
      var x = document.getElementById(div_id);
      if (x.style.display === "none") {
         x.style.display = "block";
      } else {
         x.style.display = "none";
      }
   }
   </script>
"""
