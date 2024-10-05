# shell script to get install started
# you must run this as the "ams" user with sudo 
sudo apt update
sudo apt upgrade 

cd ~ams/
wget https://archive.allsky.tv/APPS/INSTALL/apt.conf -O apt.conf
wget https://archive.allsky.tv/APPS/INSTALL/pip.conf -O pip.conf
wget https://archive.allsky.tv/APPS/INSTALL/requirements.txt -O requirements.txt



#./AS7Setup.py
file='apt.conf'
while read line; do
        #echo $line 
	apt-get install -y $line
done <$file
apt install python3-venv
/usr/bin/python3 -m ensurepip
/usr/bin/python3 -m pip install --upgrade pip -i https://pypi.mirrors.ustc.edu.cn/simple/ 
file='pip.conf'
while read line; do
        #echo $line 
	/usr/bin/python3 -m pip install $line -i https://pypi.mirrors.ustc.edu.cn/simple/
done <$file

/usr/bin/python3 install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/

git clone https://github.com/mikehankey/amscams.git
cd amscams/install
./AS7Setup.py

