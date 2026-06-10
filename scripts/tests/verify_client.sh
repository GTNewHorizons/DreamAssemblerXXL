#!/usr/bin/env bash
# Checks whether the client side of the integration run passed
#
# No `set -e`: greps that legitimately find nothing must not be mistaken for
# failures. Each check feeds the explicit status instead, so every problem of
# the run gets reported, not just the first one.
set -uo pipefail
shopt -s nullglob

RUN_DIR="${RUN_DIR:?RUN_DIR must be set}"
CLIENT_DIR="${CLIENT_DIR:?CLIENT_DIR must be set}"

CLIENT_LOG="$RUN_DIR/client.log"
CLIENT_EXIT_FLAG="$RUN_DIR/client.exit"

rc=0

# Exit code recorded by run_with_exit.sh when the game closed
if [ -e "$CLIENT_EXIT_FLAG" ]; then
  exit_code=$(cat "$CLIENT_EXIT_FLAG")
else
  exit_code=missing
fi
echo "client exit code: $exit_code"
[ "$exit_code" = "0" ] || rc=1

# Progress markers dropped by HeadlessNH as the client reaches each stage
for marker in $CLIENT_LOADED_FLAG $CLIENT_JOINED_FLAG $CLIENT_SINGLEP_FLAG; do
  if [ ! -e "$RUN_DIR/$marker" ]; then
    echo "headlessnh marker missing: $marker -- client never reached the stage?"
    rc=1
  fi
done

# Crash reports
crash_reports=("$CLIENT_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  latest_crash_report="${crash_reports[-1]}"
  echo "latest crash report detected ${latest_crash_report##*/}:"
  cat "$latest_crash_report"
  rc=1
fi

# JVM fatal error logs
hs_err_logs=("$CLIENT_DIR/hs_err_pid"*.log)
if [ "${#hs_err_logs[@]}" -gt 0 ]; then
  latest_hs_err="${hs_err_logs[-1]}"
  echo "JVM fatal error log detected ${latest_hs_err##*/}:"
  cat "$latest_hs_err"
  rc=1
fi

if [ -r "$CLIENT_LOG" ]; then
  # idk can't find anything that we want to heck the logs for, but would do it here
else
  echo "client log missing or unreadable: $CLIENT_LOG"
  rc=1
fi

[ "$rc" -eq 0 ] && echo "CLIENT: pass" || echo "CLIENT: fail"
exit "$rc"