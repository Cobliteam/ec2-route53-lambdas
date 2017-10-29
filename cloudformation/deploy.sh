#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ $# -eq 0 ]; then
    set -- build -i -t
fi

if ! [ -d venv ]; then
    virtualenv venv
fi

source venv/bin/activate
pip install stacker

stacker_cmd="$1"
shift

stacker "$stacker_cmd" config.env stack.yml "$@"
