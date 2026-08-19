#!/bin/sh
# POSIX launcher: finds an interpreter, because `python3` is not what Python is
# called everywhere. No Python means the guard is off rather than the turn broken.
CDPATH=''
export CDPATH
DIR=$(cd -- "$(dirname -- "$0")" && pwd)
script="$1"; shift
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1; then
    exec "$py" "$DIR/$script" "$@"
  fi
done
exit 0
