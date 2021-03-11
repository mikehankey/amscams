uwsgi --stop /tmp/uwsgi.pid
if pgrep uwsgi; then pkill uwsgi; fi
# sudo kill -9 $(ps aux | grep 'uwsgi' | awk '{print $2}')

