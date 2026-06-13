#!/usr/bin/env bash
# Checks whether the client side of the integration run passed
#
# No `set -e`: greps that legitimately find nothing must not be mistaken for
# failures. Each check feeds the explicit status instead, so every problem of
# the run gets reported, not just the first one.
set -uo pipefail
shopt -s nullglob

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
CLIENT_MC_DIR="${CLIENT_MC_DIR:?CLIENT_MC_DIR must be set}"

CLIENT_LOG="$RUN_DIR/client.log"
CLIENT_EXIT_FLAG="$RUN_DIR/client.exit"
CLIENT_KILLED_FLAG="$RUN_DIR/client.killed"

rc=0

# Exit code recorded by run_with_exit.sh when the game closed
if [ -e "$CLIENT_EXIT_FLAG" ]; then
  exit_code=$(cat "$CLIENT_EXIT_FLAG")
else
  exit_code=missing
fi
echo "client exit code: $exit_code"

# 137/143 are fine only when we signalled the game itself, i.e.
# the client wouldn't close nicely, otherwise a non-zero code is a failure.
case "$exit_code" in
  0) ;;
  137|143) [ -e "$CLIENT_KILLED_FLAG" ] || rc=1 ;;
  *) rc=1 ;;
esac

# Progress markers dropped by HeadlessNH as the client reaches each stage
for marker in "$CLIENT_LOADED_FLAG" "$CLIENT_JOINED_FLAG" "$CLIENT_SINGLEP_FLAG"; do
  if [ ! -e "$marker" ]; then
    echo "headlessnh marker missing: $marker -- client never reached the stage?"
    rc=1
  fi
done

# Crash reports
crash_reports=("$CLIENT_MC_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  latest_crash_report="${crash_reports[-1]}"
  echo "latest crash report detected ${latest_crash_report##*/}:"
  cat "$latest_crash_report"
  rc=1
fi

# JVM fatal error logs
hs_err_logs=("$CLIENT_MC_DIR/hs_err_pid"*.log)
if [ "${#hs_err_logs[@]}" -gt 0 ]; then
  latest_hs_err="${hs_err_logs[-1]}"
  echo "JVM fatal error log detected ${latest_hs_err##*/}:"
  cat "$latest_hs_err"
  rc=1
fi

if [ -r "$CLIENT_LOG" ]; then
  # idk can't find anything that we want to heck the logs for, but would do it here
  echo ""
else
  echo "client log missing or unreadable: $CLIENT_LOG"
  rc=1
fi

[ "$rc" -eq 0 ] && echo "CLIENT: pass" || echo "CLIENT: fail"
exit "$rc"