import datetime
from lib.PipeUtil import load_json_file
import os

def mobile_service_worker(amsid, options, json_conf):

    

   out = """
const staticDevCoffee = "dev-coffee-site-v1"
const assets = [
  "/",
  "/index.html",
  "/css/style.css",
  "/js/app.js",
  "/images/coffee1.jpg",
  "/images/coffee2.jpg",
  "/images/coffee3.jpg",
  "/images/coffee4.jpg",
  "/images/coffee5.jpg",
  "/images/coffee6.jpg",
  "/images/coffee7.jpg",
  "/images/coffee8.jpg",
  "/images/coffee9.jpg",
]

self.addEventListener("install", installEvent => {
  installEvent.waitUntil(
    caches.open(staticDevCoffee).then(cache => {
      cache.addAll(assets)
    })
  )
})

self.addEventListener("fetch", fetchEvent => {
  fetchEvent.respondWith(
    caches.match(fetchEvent.request).then(res => {
      return res || fetch(fetchEvent.request)
    })
  )
})

   """
   return(out)

def get_meteors_day(station_id, date,json_conf):
   # cloud URL
   #obs_id_file = "/mnt/archive.allsky.tv/AMS1/METEORS/2023/2023_05_26/2023_05_26_OBS_IDS.info"
   #  /mnt/ams2/meteors/2023_05_26/AMS1_2023_05_26_OBS_IDS.info
   # local meteors 
   meteor_dir = "/mnt/ams2/meteors/" + date + "/" 
   meteor_index = meteor_dir + station_id + "_" + date + "_OBS_IDS.info"
   print("MI:", meteor_index)
   if os.path.exists(meteor_index) is True:
      meteors = load_json_file(meteor_index)
   else:
      meteors = []
   return(meteors)

def parse_date(options):
   now = datetime.datetime.now()
   date_str = str(now.strftime("%Y_%m_%d"))
   if "p" not in options:
      page = "0"
   else:
      page = options["p"]

   if "d" not in options:
      date = date_str 
   else:
      date = options['d'] 
   return(date, page)

def mobile_main(station_id, options, json_conf):
   date,page = parse_date(options)


   out = """

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta http-equiv="X-UA-Compatible" content="ie=edge" />
    <link rel="stylesheet" href="/ideas/css/style.css" />
    <title>AllSky7 Meteors</title>
<link rel="manifest" href="manifest.json" />
<!-- ios support -->
<link rel="apple-touch-icon" href="/images/icons/icon-72x72.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-96x96.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-128x128.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-144x144.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-152x152.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-192x192.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-384x384.png" />
<link rel="apple-touch-icon" href="/images/icons/icon-512x512.png" />
<meta name="apple-mobile-web-app-status-bar" content="#db4938" />
<meta name="theme-color" content="#db4938" />

  </head>
  <body>
    <main>
      <nav>
        <h1>AllSky7 Meteors</h1>
        <ul>
          <li>Home</li>
          <li>Meteors</li>
          <li>Non-Meteors</li>
          <li>Weather</li>
          <li>Network</li>
          <li>Calibration</li>
          <li>AI</li>
          <li>Config</li>
        </ul>
      </nav>

      <div class="alerts">
<input id="startDate" class="form-control" type="date" value="2023-05-28"/>

      </div>
        
      <div class="container"></div>



    </main>
    <script src="js/app.js?d={:s}&p={:s}"></script>
    <script src="https://kit.fontawesome.com/f3f9f77a06.js" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap-  datetimepicker/4.17.47/js/bootstrap-datetimepicker.min.js"></script>
  </body>
</html>

   """.format(date, page)
   return(out)

def mobile_css(amsid, options, json_conf):
   # keep css outside of app in .css file
   out = """
   """
   return(out)

def mobile_js(station_id, options, json_conf):
   # dynamic JS. 
   date,page = parse_date(options)
   meteors = get_meteors_day(station_id, date, json_conf)

   coff = "const coffees = ["
   for mfile, mdatetime in meteors:
      mdate,mtime = mdatetime.split(" ")
      mdate = mdate.replace("-", "_")
      mvthumb = "/meteors/" + mdate + "/" + mfile + "-stacked-obj-tn.jpg"
      mthumb = "/mnt/ams2/meteors/" + mdate + "/" + mfile + "-stacked-obj-tn.jpg"
      coff += ' {name: "' + mdate + '", image: "' + mvthumb + '" }, '
   coff += "]"
   print("COFF", coff)
   out = """
const container = document.querySelector(".container")
{:s}
   """.format(coff)

   out += """
const showCoffees = () => {
  let output = ""
  coffees.forEach(
    ({ name, image }) =>
      (output += `
              <div class="card">
                <img class="card--avatar" src=${image} />
                <h1 class="card--title">${name}</h1>
                <div style="float: left">
                   <a class="card--link" href="#">Trash 1</a>
                   <a class="card--link" href="#">Trash 2</a>
                   <a class="card--link" href="#">Trash 3</a>
                </div>
              </div>
              `)
  )
  container.innerHTML = output
}

document.addEventListener("DOMContentLoaded", showCoffees)


if ("serviceWorker" in navigator) {
  window.addEventListener("load", function() {
    navigator.serviceWorker
      .register("/serviceWorker.js")
      .then(res => console.log("service worker registered"))
      .catch(err => console.log("service worker not registered", err))
  })
}
   """
   return(out)

def mobile_manifest(amsid, options, json_conf):
   out = """
{
  "name": "AllSky7 Meteors",
  "short_name": "AllSk7Meteors",
  "start_url": "index.html",
  "display": "standalone",
  "background_color": "#fdfdfd",
  "theme_color": "#db4938",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/images/icons/icon-72x72.png",
      "type": "image/png", "sizes": "72x72"
    },
    {
      "src": "/images/icons/icon-96x96.png",
      "type": "image/png", "sizes": "96x96"
    },
    {
      "src": "/images/icons/icon-128x128.png",
      "type": "image/png","sizes": "128x128"
    },
    {
      "src": "/images/icons/icon-144x144.png",
      "type": "image/png", "sizes": "144x144"
    },
    {
      "src": "/images/icons/icon-152x152.png",
      "type": "image/png", "sizes": "152x152"
    },
    {
      "src": "/images/icons/icon-192x192.png",
      "type": "image/png", "sizes": "192x192"
    },
    {
      "src": "/images/icons/icon-384x384.png",
      "type": "image/png", "sizes": "384x384"
    },
    {
      "src": "/images/icons/icon-512x512.png",
      "type": "image/png", "sizes": "512x512"
    }
  ]
}
   """
   return(out)
