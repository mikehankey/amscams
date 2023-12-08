#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Install pyenv
if ! command -v pyenv >/dev/null 2>&1; then
	    curl https://pyenv.run | bash

	        # Add pyenv to the path for this session. For permanent setup, add these lines to your profile (e.g., ~/.bash_profile)
		    export PATH="$HOME/.pyenv/bin:$PATH"
		        eval "$(pyenv init -)"
			    eval "$(pyenv virtualenv-init -)"
fi

# Install pyenv-virtualenv plugin if not already installed
if [ ! -d "$(pyenv root)/plugins/pyenv-virtualenv" ]; then
	    git clone https://github.com/pyenv/pyenv-virtualenv.git "$(pyenv root)/plugins/pyenv-virtualenv"
	        eval "$(pyenv virtualenv-init -)"
fi

# Get the latest Python version and install it
latest_python_version=$(pyenv install -l | grep -E '^\s*3\.[6789]' | tail -1 | tr -d '[:space:]')
pyenv install $latest_python_version

# Create a virtual environment with the latest Python version
env_name="my_latest_python_env"
pyenv virtualenv $latest_python_version $env_name

# Set the virtual environment globally, or use 'pyenv local $env_name' for a specific project
pyenv global $env_name

echo "Virtual environment '$env_name' created with Python $latest_python_version"

