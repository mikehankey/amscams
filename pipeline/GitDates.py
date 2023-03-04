import sys
from calendar import monthrange
import json
import datetime
import os
from lib.PipeUtil import load_json_file, save_json_file, get_template

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
def network_by_day(year):
   event_stats_file = "/mnt/f/EVENTS/event_stats.json"
   today = (datetime.datetime.now() - datetime.timedelta(days = 0)).strftime("%Y_%m_%d")
   current_year, current_month, current_day = today.split("_")
   years = ['2023', '2022', '2021']
   start_year = min(years)

   year_span = int(current_year) - int(start_year)
   all_days = []
   stats = {}
   for year in years :
      evdir = "/mnt/f/EVENTS/" + year 
      #just do current year
      if year == current_year:
         end_mon = current_month
         end_day = current_day
      else:
         end_mon = 12
      for mon in range(1,int(end_mon) + 1):
         if mon == int(end_mon) and year == current_year:
            end_days = int(current_day)
         else:
            end_days = int(monthrange(int(year), mon)[1])
         for day in range(1,end_days + 1) :
            if mon < 10:
               smon = "0" + str(mon)
            else:
               smon = str(mon)
            if day < 10:
               sday = "0" + str(day)
            else:
               sday = str(day)

            date_str = year + "_" + smon + "_" + sday
            this_dt = datetime.datetime.strptime(date_str, "%Y_%m_%d")
            day_diff = (datetime.datetime.now() - this_dt).total_seconds() / 60 / 60 / 24
            all_days.append((year + "_" +  smon + "_" + sday))
            ev_file = "/mnt/f/EVENTS/" + year + "/" + smon + "/" + sday + "/" + date_str + "_ALL_EVENTS.json"
            if os.path.exists(ev_file) :
               data = load_json_file(ev_file)
            else:
               data = []
            stats[date_str] = {}
            stats[date_str]['total_events'] = len(data) 
   for st in stats:
      print(st, stats[st])
      if stats[st]['total_events'] == 0:
         cmd = "./AllSkyNetwork.py do_all " + st
         #print(cmd)
         #os.system(cmd)


   save_json_file(event_stats_file, stats)
   print("saved:", event_stats_file)


def obs_by_day(year):
   js_data = []
   stats = {}
   stats_file = "/mnt/ams2/meteors/" + station_id + "_STATS_BY_DAY.json"
   data_file = "/mnt/ams2/meteors/" + station_id + "_OBS_IDS_{:s}.json".format(year)
   data = load_json_file(data_file)
   for d in data:
      date = d[1].split(" ")[0]
      date = date.replace("-", "_")
      if date not in stats:
         stats[date] = {}
         stats[date]['meteors'] = 1
      else:
         stats[date]['meteors'] += 1
   
   save_json_file(stats_file, stats)

 
   date_dt = datetime.datetime.now()
   day_of_year = int(date_dt.strftime('%j'))
   # make the year days
   for i in range(0,int(day_of_year)):
      minus = (date_dt - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
      #day_of_year = minus.strftime('%j')
      tdate = minus
      y,m,d = minus.split("_")
      date_str = y + "_" + m + "_" + d
      di = day_of_year - i
      print("M", minus)
      if minus in stats:
         mets = stats[minus]['meteors']
      else:
         mets = 0
      if mets == 0:
         level = 0
      elif 0 < mets <= 25:
         level = 1
      elif 25 < mets <= 50:
         level = 2
      elif mets > 50:
         level = 3 
      print(di, y,m,d, mets, level)
      js_data.append((di, date_str, mets, level))

   js_data = sorted(js_data, key=lambda x: (x[0]), reverse=False)

   html = get_template("FlaskTemplates/git_dates.html")
   style = get_template("FlaskTemplates/git_dates.css")
   javascript = get_template("FlaskTemplates/git_dates.js")
   html = html.replace("{STYLE}", style)
   html = html.replace("{JAVASCRIPT}", javascript)

   html = html.replace("{DATA}", json.dumps(js_data))
   html = html.replace("{STATION_ID}", station_id)
   out = open("/mnt/ams2/meteor_nav_" + y + ".html", "w")
   out.write(html)
   print("/mnt/ams2/meteor_nav_" + y + ".html")

def template():
   html = """

<style>
/* Article - https://bitsofco.de/github-contribution-graph-css-grid/ */

/* Grid-related CSS */

:root {
  --square-size: 15px;
  --square-gap: 5px;
  --week-width: calc(var(--square-size) + var(--square-gap));
}

.months { grid-area: months; }
.days { grid-area: days; }
.squares { grid-area: squares; }

.gal {
  padding: 20px;
  margin: 20px;
  width: 100%;
  display: block;

}

.graph {
  display: inline-grid;
  grid-template-areas: "empty months"
                       "days squares";
  grid-template-columns: auto 1fr;
  grid-gap: 10px;
}

.months {
  list-style-type: none;
  display: grid;
  grid-template-columns: calc(var(--week-width) * 4) /* Jan */
                         calc(var(--week-width) * 4) /* Feb */
                         calc(var(--week-width) * 4) /* Mar */
                         calc(var(--week-width) * 5) /* Apr */
                         calc(var(--week-width) * 4) /* May */
                         calc(var(--week-width) * 4) /* Jun */
                         calc(var(--week-width) * 5) /* Jul */
                         calc(var(--week-width) * 4) /* Aug */
                         calc(var(--week-width) * 4) /* Sep */
                         calc(var(--week-width) * 5) /* Oct */
                         calc(var(--week-width) * 4) /* Nov */
                         calc(var(--week-width) * 5) /* Dec */;
}

.days,
.squares {
  list-style-type: none;
  display: grid;
  grid-gap: var(--square-gap);
  grid-template-rows: repeat(7, var(--square-size));
}

.squares {
  list-style-type: none;
  grid-auto-flow: column;
  grid-auto-columns: var(--square-size);
}


/* Other styling */

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
  font-size: 12px;
  color: red;
  background: #000000;
}

.graph {
  padding: 20px;
  border: 1px #e1e4e8 solid;
  margin: 20px;
}

.days li:nth-child(odd) {
  list-style-type: none;
  visibility: hidden;
  list-style-type: none;
}

.squares li {
  list-style-type: none;
  background-color: #ebedf0;
}

.squares li[data-level="1"] {
  background-color: #c6e48b;
}

.squares li[data-level="2"] {
  background-color: #7bc96f;
}

.squares li[data-level="3"] {
  background-color: #196127;
}
.tooltip {
  list-style-type: none;
  position: relative;
  display: inline-block;
  border-bottom: 0px dotted black;
}

.tooltip .tooltiptext {
  list-style-type: none;
  visibility: hidden;
  width: 120px;
  background-color: black;
  color: #fff;
  text-align: center;
  border-radius: 6px;
  padding: 5px 0;
  
  /* Position the tooltip */
  position: absolute;
  z-index: 1;
  top: -5px;
  right: 105%;
}

.tooltip:hover .tooltiptext {
  list-style-type: none;
  visibility: visible;
}

.met_thumb {
   float: left;
   border: 5px #000000 solid;
}

.clearfix {
  clear: both;
  display: block;
}

</style>

<div id="container" style="width: 80%">

<div id="metgal" class="gal" >
METEOR GALLERY
</div>

<div id="metgal" class="clearfix" >
</div>

<div class="graph">
    <ul class="months">
      <li>Jan</li>
      <li>Feb</li>
      <li>Mar</li>
      <li>Apr</li>
      <li>May</li>
      <li>Jun</li>
      <li>Jul</li>
      <li>Aug</li>
      <li>Sep</li>
      <li>Oct</li>
      <li>Nov</li>
      <li>Dec</li>
    </ul>
    <ul class="days">
      <li>Sun</li>
      <li>Mon</li>
      <li>Tue</li>
      <li>Wed</li>
      <li>Thu</li>
      <li>Fri</li>
      <li>Sat</li>
    </ul>
    <ul class="squares">
      <!-- added via javascript -->
    </ul>
  </div>
</div>
<script>

// Add squares
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
data = {DATA}
for (var i = 1; i < 365; i++) {
  //const level = Math.floor(Math.random() * 3);  
  if (i <= data.length) {
  var date = data[i-1][1] + ""
  var mets = data[i-1][2]
  var level = data[i-1][3]
  console.log(date)
	squares.insertAdjacentHTML('beforeend', `<li class="tooltip" onclick="show_day('{STATION_ID}', ${date})" data-level="${level}"><span class="tooltiptext">${date} ${mets} meteors</span></li>`);
        }

}
</script>

   """
   return(html)

def git_dates_html(data, save_file, title=""):
   # take in list of data then make the git nav and save the html
   print("")


if __name__ == "__main__":
   if sys.argv[1] == "network":
      year = sys.argv[2]
      network_by_day(year)
   else:
      obs_by_day(sys.argv[1])
