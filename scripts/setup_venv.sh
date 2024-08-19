#!/usr/bin/env bash

set -ex

ROOT_DIR=$( cd "$( dirname "$0" )" && cd .. && pwd )

cd "$ROOT_DIR"

if [ -d venv ]; then
  echo 'venv directory already exists!'
  exit 1
fi

python3.12 -m venv venv

source ./venv/bin/activate

echo 'Installing JULE...'
python -m pip install -e .

echo 'Installing DEV packages...'
python -m pip install -r requirements-dev.txt
