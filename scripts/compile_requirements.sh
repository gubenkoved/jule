#!/usr/bin/env bash

ROOT_DIR=$( cd "$( dirname "$0" )" && cd .. && pwd )

cd "$ROOT_DIR"

[[ "$*" != *"--upgrade"* ]] && echo 'HINT: Use "--upgrade" to upgrade packages'

pip-compile "$@" > requirements.txt
pip-compile "$@" requirements-dev.in -c requirements.txt > requirements-dev.txt
