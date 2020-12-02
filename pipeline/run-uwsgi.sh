uwsgi --shared-socket [::]:80 --http =0 --thunder-lock --uid 1000 --gid 1000 --wsgi-file flaskAdmin.py --callable app --processes 4 --threads 2 --stats 127.0.0.1:9191 --check-static /mnt/ams2/ --pidfile=/tmp/uwsgi.pid 

