#!/bin/bash

# use bash strict mode
set -euo pipefail

mkdir -p $HOME/www/python/src

python3 -m venv $HOME/www/python/venv

# activate it
source $HOME/www/python/venv/bin/activate

# upgrade pip inside the venv and add support for the wheel package format
pip install -U pip wheel

# install some concrete packages
pip install requests packaging wikitextparser python-dateutil certifi --upgrade

# toolforge-jobs run webvenv --image python3.11 --command "$HOME/web_sh/web_venv.sh"
