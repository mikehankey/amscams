uwsgi --http 0.0.0.0:80 --wsgi-file flaskAdmin.py --callable app --processes 4 --threads 2 --stats 127.0.0.1:9191 --check-static /mnt/ams2/ --pidfile=/tmp/uwsgi.pid

