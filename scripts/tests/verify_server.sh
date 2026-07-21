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
DUAL_SERVER_LOG="$RUN_DIR/dual_test_server.log"

HQA_RESULT_JSON="$RUN_DIR/horizonqa-result.json"

rc=0

# Sets a non-zero exit code, with the provided reason
fail() {
  echo "FAIL: $*"
  rc=1
}

# Exit code recorded by run_with_exit.sh when the JVM stopped
if [ -e "$SERVER_EXIT_FLAG" ]; then
  exit_code=$(cat "$SERVER_EXIT_FLAG")
else
  exit_code=missing
fi
echo "server exit code: $exit_code"
[ "$exit_code" = "0" ] || fail "server exited with non-zero code: $exit_code"

# Crash reports
crash_reports=("$SERVER_DIR/crash-reports/crash"*.txt)
if [ "${#crash_reports[@]}" -gt 0 ]; then
  latest_crash_report="${crash_reports[-1]}"
  fail "found server crash report at ${latest_crash_report##*/}:"
  cat "$latest_crash_report"
fi

# JVM fatal error logs
hs_err_logs=("$SERVER_DIR/hs_err_pid"*.log)
if [ "${#hs_err_logs[@]}" -gt 0 ]; then
  latest_hs_err="${hs_err_logs[-1]}"
  fail "JVM fatal error log detected ${latest_hs_err##*/}:"
  cat "$latest_hs_err"
fi

if [ -r "$SERVER_LOG" ]; then
  if grep --quiet --fixed-strings 'Fatal errors were detected' "$SERVER_LOG"; then
    fail "fatal errors detected:"
    grep -n --fixed-strings 'Fatal errors were detected' "$SERVER_LOG"
  fi

  if grep --quiet --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' \
    "$SERVER_LOG"; then
    fail "server force stopped:"
    grep -n --fixed-strings 'The state engine was in incorrect state ERRORED and forced into state SERVER_STOPPED' "$SERVER_LOG"
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
      fail "server had duplicate files, environment cant be guaranteed to contain correct versions:"
      echo "$dupes"
    fi
  fi

  if grep --quiet --fixed-strings 'Exception stopping the server' "$SERVER_LOG"; then
    fail "server didn't shut down cleanly:"
    grep -n --fixed-strings 'Exception stopping the server' "$SERVER_LOG"
  fi
else
  fail "server log missing or unreadable: $SERVER_LOG"
fi

# Server side of what was emitted during the dual tests
if [ -e "$HQA_RESULT_JSON" ]; then
  hqa_status=$(jq -r '.status // empty' "$HQA_RESULT_JSON")
  if [ "$hqa_status" != "passed" ]; then
    failed_tests=$(jq -r '.counts.failed // 0' "$HQA_RESULT_JSON")
    if ! [[ "$failed_tests" =~ ^[0-9]+$ ]]; then
      fail "could not read HQA test failure count from $HQA_RESULT_JSON (got: '$failed_tests')"
    else
      fail "HQA tests had $failed_tests failures (status: ${hqa_status:-missing})"
    fi
  else
    echo "HQA tests passed!"
  fi
else
  fail "HQA execution result json at $HQA_RESULT_JSON is missing - did the tests not get run because the client failed to start? (see the verify-client step)"
fi


[ "$rc" -eq 0 ] && echo "SERVER: pass" || echo "SERVER: fail"
exit "$rc"