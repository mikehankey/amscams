# shell script to get install started
# you must run this as the "ams" user with sudo 
sudo apt update
sudo apt upgrade 

cd ~ams/
wget https://archive.allsky.tv/APPS/INSTALL/apt.conf -O apt.conf
wget https://archive.allsky.tv/APPS/INSTALL/pip.conf -O pip.conf
wget https://archive.allsky.tv/APPS/INSTALL/requirements.conf -O requirements.conf



#./AS7Setup.py
file='apt.conf'
while read line; do
        #echo $line 
	apt-get install -y $line
done <$file
apt install python3-venv
/usr/bin/python3 -m ensurepip
/usr/bin/python3 -m pip install --upgrade pip
file='pip.conf'
while read line; do
        #echo $line 
	/usr/bin/python3 -m pip install $line
done <$file

/usr/bin/python3 install -r requirements.txt

git clone https://github.com/mikehankey/amscams.git
cd amscams/install
./AS7Setup.py

