# shell script to get install started
# you must run this as the "ams" user with sudo 

cd ~ams/
wget https://archive.allsky.tv/APPS/INSTALL/apt.conf -O apt.conf
wget https://archive.allsky.tv/APPS/INSTALL/pip.conf -O pip.conf



#./AS7Setup.py
file='apt.conf'
while read line; do
        #echo $line 
	apt-get install -y $line
done <$file

file='pip.conf'
while read line; do
        #echo $line 
	python3 -m pip install $line
done <$file

git clone https://github.com/mikehankey/amscams.git
cd amscams/install
./AS7Setup.py

