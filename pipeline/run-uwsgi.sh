#./stop-uwsgi.sh
#sleep 1
UID=$(id -u ams)
GID=$(id -g ams)
#/usr/local/bin/uwsgi --shared-socket [::]:80 --http =0 --thunder-lock --uid $UID --gid $GID --wsgi-file flaskAdmin.py --callable app --processes 4 --threads 2 --stats 127.0.0.1:9191 --check-static /mnt/ams2/ --pidfile=/tmp/uwsgi.pid 


/usr/local/bin/uwsgi --shared-socket [::]:80 --thunder-lock --http =0 --uid $UID --gid $GID --wsgi-file flaskAdmin.py --callable app --processes 4 --threads 2 --check-static /mnt/ams2/ --pidfile=/tmp/uwsgi.pid 

