#!/bin/sh
# POSIX launcher: find an interpreter and run emit.py. No Python means the monitor is off, not the turn broken.
CDPATH=''
export CDPATH
DIR=$(cd -- "$(dirname -- "$0")" && pwd)
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1; then
    exec "$py" "$DIR/emit.py" "$@"
  fi
done
exit 0
