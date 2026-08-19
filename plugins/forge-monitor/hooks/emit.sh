#!/bin/sh
# POSIX launcher. The only job is finding an interpreter, because Claude Code's
# hook `command` is a fixed string and `python3` is not what Python is called
# everywhere. Deliberately /bin/sh and free of bashisms: macOS ships bash 3.2
# and Windows may have neither.
#
# If no Python is found this exits 0 and the monitor is simply off. That is the
# correct failure for an observer - the alternative is breaking a turn on a
# machine that was only ever missing an optional tool.
CDPATH=''
export CDPATH
DIR=$(cd -- "$(dirname -- "$0")" && pwd)
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1; then
    exec "$py" "$DIR/emit.py" "$@"
  fi
done
exit 0
