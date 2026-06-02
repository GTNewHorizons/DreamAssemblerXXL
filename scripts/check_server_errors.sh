#!/usr/bin/env bash
set -euo pipefail

# Taken from https://github.com/MalTeeez/packscripts-auto-builds/blob/gtnh-daily/packaging/scripts/check_server_errors.sh

# bashsupport disable=BP5006 # Global environment variables
WORKDIR=$1
CRASH="crash-reports"
SERVERLOG="server.log"

cd $WORKDIR

# enable nullglob to get 0 results when no match rather than the pattern
shopt -s nullglob

if [ ! -r "$SERVERLOG" ]; then
  printf 'check_server_errors: %s missing or unreadable\n' "$SERVERLOG" >&2
  exit 1
fi

# store matches in array
crash_reports=("$WORKDIR/$CRASH/crash"*.txt)

# if array not empty there are crash_reports
if [ "${#crash_reports[@]}" -gt 0 ]; then
  # get the latest crash_report from array
  latest_crash_report="${crash_reports[-1]}"
  {
    printf 'Latest crash report detected %s:\n' "${latest_crash_report##*/}"
    cat "$latest_crash_report"
  } >&2
  exit 1
fi

if grep --quiet --fixed-strings 'Fatal errors were detected' "$SERVERLOG"; then
  {
    printf 'Fatal errors detected:\n'
    grep -n --fixed-strings 'Fatal errors were detected' "$SERVERLOG"
  } >&2
  exit 1
fi

if grep --quiet --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' \
  "$SERVERLOG"; then
  {
    printf 'Server force stopped:\n'
    grep -n --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' "$SERVERLOG"
  } >&2
  exit 1
fi

if grep --quiet --fixed-strings 'Duplicate mod found:' "$SERVERLOG"; then
  dupes=$(grep --fixed-strings 'Duplicate mod found:' "$SERVERLOG" \
    | while read -r line || [ -n "$line" ]; do
        a=$(echo "$line" | grep -oP '(?<=\()[^)]+\.jar(?=\))' | head -1)
        b=$(echo "$line" | grep -oP '(?<=\()[^)]+\.jar(?=\))' | tail -1)
        [ "$a" != "$b" ] && echo "$line" || true
      done)
  if [ -n "$dupes" ]; then
    {
      printf 'Server had duplicate files, environment cant be guaranteed to contain indev version:\n'
      echo "$dupes"
    } >&2
    exit 1
  fi
fi

if grep --quiet --fixed-strings 'Exception stopping the server' "$SERVERLOG"; then
  {
    printf "Server didn't shut down cleanly:\n"
    grep -n --fixed-strings 'Exception stopping the server' "$SERVERLOG"
  } >&2
  exit 1
fi

printf 'No errors detected with server run\n'
exit 0