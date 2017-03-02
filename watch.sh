#!/bin/bash -u

cd "$(dirname "$0")"

# usage: ./watch <in> <out>

while true; do
    inotifywait -r -e close_write,moved_to,create "$1" "$2"
    ./gen.py "$1" "$2"
done
