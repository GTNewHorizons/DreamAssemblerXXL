#!/usr/bin/env bash

BASEDIR=$(dirname "$0")

"$BASEDIR/isort.sh"
status=$?
[ $status -eq 0 ] && echo "msuccess!" || exit 1
"$BASEDIR/black.sh"
status=$?
[ $status -eq 0 ] && echo "success!" || exit 1
"$BASEDIR/mypy.sh"
status=$?
[ $status -eq 0 ] && echo "success!" || exit 1
"$BASEDIR/lint.sh"
status=$?
[ $status -eq 0 ] && echo "success!" || exit 1