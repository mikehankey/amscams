uwsgi --stop /tmp/uwsgi.pid

sudo kill -9 $(ps aux | grep 'uwsgi' | awk '{print $2}')

