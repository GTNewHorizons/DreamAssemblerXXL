#!/usr/bin/env bash

flags=()
printf 'Running black formatting\n'
if [ -n "${CI}" ]; then
  flags=(--check)
fi

poetry run black "$@" "${flags[@]}" src  || exit 1