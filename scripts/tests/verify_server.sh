#!/usr/bin/env bash
# Checks whether the server side of the integration run passed
#
# initially based on https://github.com/GTNewHorizons/GTNH-Actions-Workflows/blob/master/scripts/test_no_error_reports
#
# No `set -e`: greps that legitimately find nothing must not be mistaken for
# failures. Each check feeds the explicit status instead, so every problem of
# the run gets reported, not just the first one.
set -uo pipefail
shopt -s nullglob

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
SERVER_DIR="${SERVER_DIR:?SERVER_DIR must be set}"

SERVER_LOG="$RUN_DIR/server.log"

rc=0

# Exit code recorded by run_with_exit.sh when the JVM stopped
if [ -e "$SERVER_EXIT_FLAG" ]; then
  exit_code=$(cat "$SERVER_EXIT_FLAG")
else
  exit_code=missing
fi
echo "server exit code: $exit_code"
[ "$exit_code" = "0" ] || rc=1

# Crash reports
crash_reports=("$SERVER_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  latest_crash_report="${crash_reports[-1]}"
  echo "latest crash report detected ${latest_crash_report##*/}:"
  cat "$latest_crash_report"
  rc=1
fi

# JVM fatal error logs
hs_err_logs=("$SERVER_DIR/hs_err_pid"*.log)
if [ "${#hs_err_logs[@]}" -gt 0 ]; then
  latest_hs_err="${hs_err_logs[-1]}"
  echo "JVM fatal error log detected ${latest_hs_err##*/}:"
  cat "$latest_hs_err"
  rc=1
fi

if [ -r "$SERVER_LOG" ]; then
  if grep --quiet --fixed-strings 'Fatal errors were detected' "$SERVER_LOG"; then
    echo "fatal errors detected:"
    grep -n --fixed-strings 'Fatal errors were detected' "$SERVER_LOG"
    rc=1
  fi

  if grep --quiet --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' \
    "$SERVER_LOG"; then
    echo "server force stopped:"
    grep -n --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' "$SERVER_LOG"
    rc=1
  fi

  # Duplicate mods only count when the two jar names in the line differ;
  # a mod colliding with itself is just a jar being seen twice.
  if grep --quiet --fixed-strings 'Duplicate mod found:' "$SERVER_LOG"; then
    dupes=$(grep --fixed-strings 'Duplicate mod found:' "$SERVER_LOG" \
      | while read -r line || [ -n "$line" ]; do
          a=$(echo "$line" | grep -oP '(?<=\()[^)]+\.jar(?=\))' | head -1)
          b=$(echo "$line" | grep -oP '(?<=\()[^)]+\.jar(?=\))' | tail -1)
          [ "$a" != "$b" ] && echo "$line" || true
        done)
    if [ -n "$dupes" ]; then
      echo "server had duplicate files, environment cant be guaranteed to contain correct versions:"
      echo "$dupes"
      rc=1
    fi
  fi

  if grep --quiet --fixed-strings 'Exception stopping the server' "$SERVER_LOG"; then
    echo "server didn't shut down cleanly:"
    grep -n --fixed-strings 'Exception stopping the server' "$SERVER_LOG"
    rc=1
  fi
else
  echo "server log missing or unreadable: $SERVER_LOG"
  rc=1
fi

[ "$rc" -eq 0 ] && echo "SERVER: pass" || echo "SERVER: fail"
exit "$rc"