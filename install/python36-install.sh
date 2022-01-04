sudo apt install build-essential checkinstall
sudo apt install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev

# Retrieve and unzip package
wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tar.xz
tar xvf Python-3.6.0.tar.xz

# Make
cd Python-3.6.0/
./configure
sudo make altinstall
