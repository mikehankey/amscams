


function show_day(station_id, date) {
   var tdate = date.toString()
   var gal_html = ""
   var y = tdate.substr(0,4)
   var m = tdate.substr(4,2)
   var d = tdate.substr(6,2)
   var ud = "https://archive.allsky.tv/" + station_id + "/METEORS/" + y + "/" + y + "_" + m + "_" + d + "/" 
   var u = ud + y + "_" + m + "_" + d + "_OBS_IDS.info"
   console.log(y,m,d, u)
   fetch(u) 
      .then(response => {
         if(!response.ok) {
            throw new Error("HTTP error" + response.status); 
         }
         return response.json();
      })
      .then(json => {
         for (i=0; i < json.length; i++) {
            console.log("ROW", json[i])
            img_url = ud +  station_id + "_" + json[i][0] + "-prev.jpg"
            gal_html += "<img width=360 height=180 class='met_thumb' src=" +  img_url + ">"
         }
               document.getElementById("metgal").innerHTML = gal_html;
      })
   }

const squares = document.querySelector('.squares');
// this could be a fetch based on the station and year ?
data = {DATA}
for (var i = 1; i < 365; i++) {
  if (i <= data.length) {
  var date = data[i-1][1] + ""
  var mets = data[i-1][2]
  var level = data[i-1][3]
	squares.insertAdjacentHTML('beforeend', `<li class="tooltip" onclick="show_day('{STATION_ID}', ${date})" data-level="${level}"><span class="tooltiptext">${date} ${mets} meteors</span></li>`);
        }

}

