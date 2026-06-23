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
DUAL_CLIENT_LOG="$RUN_DIR/dual_test_client.log"

rc=0

# Sets a non-zero exit code, with the provided reason
fail() {
  echo "FAIL: $*"
  rc=1
}

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
  137|143)
    [ -e "$CLIENT_KILLED_FLAG" ] || fail "client exited with $exit_code but we never signalled it"
    ;;
  *) fail "client exited with non-zero code: $exit_code" ;;
esac

# Progress markers dropped by HeadlessNH as the client reaches each stage
for marker in "$CLIENT_LOADED_FLAG" "$CLIENT_JOINED_FLAG" "$CLIENT_SINGLEP_FLAG"; do
  if [ ! -e "$marker" ]; then
    fail "headlessnh marker missing: $marker -- client never reached the stage?"
  fi
done

# Result of the dual tests run while the client was connected to the server
if [ -e "$DUAL_EXIT_FLAG" ]; then
  dual_exit=$(cat "$DUAL_EXIT_FLAG")
  echo "dual test exit code: $dual_exit"
  [ "$dual_exit" = "0" ] || fail "dual tests exited with non-zero code: $dual_exit"
else
  fail "dual test exit flag missing: $DUAL_EXIT_FLAG -- dual tests never ran"
fi

# Crash reports
crash_reports=("$CLIENT_MC_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  latest_crash_report="${crash_reports[-1]}"
  fail "found client crash report at ${latest_crash_report##*/}:"
  cat "$latest_crash_report"
fi

# JVM fatal error logs
hs_err_logs=("$CLIENT_MC_DIR/hs_err_pid"*.log)
if [ "${#hs_err_logs[@]}" -gt 0 ]; then
  latest_hs_err="${hs_err_logs[-1]}"
  fail "JVM fatal error log detected ${latest_hs_err##*/}:"
  cat "$latest_hs_err"
fi

if [ ! -r "$CLIENT_LOG" ]; then
  fail "client log missing or unreadable: $CLIENT_LOG"
fi

# Client side of what was emitted during the dual tests
if [ -r "$DUAL_CLIENT_LOG" ]; then
  if grep --quiet --fixed-strings 'PLACEHOLDER_CLIENT_DUAL_ERROR' "$DUAL_CLIENT_LOG"; then
    fail "dual test client log flagged a problem:"
    grep -n --fixed-strings 'PLACEHOLDER_CLIENT_DUAL_ERROR' "$DUAL_CLIENT_LOG"
  fi
else
  echo "dual test client log missing or unreadable: $DUAL_CLIENT_LOG"
fi

[ "$rc" -eq 0 ] && echo "CLIENT: pass" || echo "CLIENT: fail"
exit "$rc"