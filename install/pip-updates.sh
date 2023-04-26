sudo apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages sysstat
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages python3-mpltoolkits.basemap
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages libgeos-dev
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages libproj-dev
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages redis-server
apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages sqlite3

apt install imagemagick
python3 -m pip install suntime
python3 -m pip install flask
python3 -m pip install psutil
python3 -m pip install uwsgi
#python3 -m pip install --upgrade cython numpy pyshp six
python3 -m pip install shapely --no-binary shapely
python3 -m pip install geopy
python3 -m pip install pymap3d

# REDIS SETUP
#supervised systemd
#bind 127.0.0.1 ::1
#vi /etc/redis/redis.conf 
# systemctl restart redis.service


# edit conf add service
python3 -m pip install redis
python3 -m pip install simplekml
python3 -m pip install boto3 
python3 -m pip install simplejson
python3 -m pip install flask_httpauth
python3 -m pip install flask-dynamo
python3 -m pip install timezonefinder
python3 -m pip install pylunar
python3 -m pip install lxml
python3 -m pip install beautifulsoup4
python3 -m pip install photutils
python3 -m pip install prettytable
python3 -m pip install requests
python3 -m pip install tqdm 
python3 -m pip install imutils
