#!/usr/bin/env bash

set -ex

ROOT_DIR=$( cd "$( dirname "$0" )" && cd .. && pwd )
VENV_DIR=".venv"

cd "$ROOT_DIR"

if [ -d "$VENV_DIR" ]; then
  echo 'venv directory already exists!'
  exit 1
fi

python3.12 -m venv "$VENV_DIR"

source "./$VENV_DIR/bin/activate"

echo 'Installing requirements...'
python -m pip install -r requirements.txt

echo 'Installing JULE as editable...'
python -m pip install -e .

echo 'Installing DEV packages...'
python -m pip install -r requirements-dev.txt
