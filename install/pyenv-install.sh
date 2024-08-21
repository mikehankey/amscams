sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils \
tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git

curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

#curl https://pyenv.run | bash

echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

source ~/.bashrc
pyenv install 3.12.3
pyenv virtualenv 3.12.3 ams
pyenv local ams
pyenv global ams
pyenv activate ams
python3 -m pip install --upgrade pip

# install requirements from file
python3 -m pip install -r requirements.txt

# for crons:
# use shebang: #!/home/ams/.pyenv/shims/python3.12
# * * * * * export PATH="/home/username/.pyenv/bin:$PATH"; eval "$(pyenv init -)"; eval "$(pyenv virtualenv-init -)"; pyenv activate myenv; python /path/to/your/script.py