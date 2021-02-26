uwsgi --stop /tmp/uwsgi.pid
if pgrep uwsgi; then pkill uwsgi; fi

