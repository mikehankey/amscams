
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages python3-mpltoolkits.basemap
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages libgeos-dev
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages libproj-dev
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages redis-server

apt install imagemagick
pip3 install suntime
pip3 install flask
pip3 install psutil
pip3 install uwsgi
#cartopy
#pip3 install --upgrade cython numpy pyshp six
pip3 install shapely --no-binary shapely
pip3 install geopy
pip3 install cartopy
pip3 install pymap3d

# REDIS SETUP
#supervised systemd
#bind 127.0.0.1 ::1
#vi /etc/redis/redis.conf 
# systemctl restart redis.service


# edit conf add service
pip3 install redis
pip3 install simplekml
pip3 install boto3 
pip3 install simplejson
pip3 install flask_httpauth
pip3 install flask-dynamo
