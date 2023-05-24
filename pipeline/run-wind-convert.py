UID=$(id -u ams)
GID=$(id -g ams)


/usr/local/bin/uwsgi --shared-socket [::]:8080 --thunder-lock --http =0 --uid $UID --gid $GID --wsgi-file wind_convert.py --callable app --processes 4 --threads 2 --check-static /mnt/ams2/ --pidfile=/tmp/uwsgi-wind.pid 

