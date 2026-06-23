#!/usr/bin/env bash
# Tiny wrapper to run a command and record its exit code to a specified file.

set -uo pipefail

exit_file=$1
shift

"$@"
echo "$?" > "$exit_file"