#!/usr/bin/env bash

flags=()
printf 'Running Running mypy type validation\n'
if [ -n "${CI}" ]; then
  flags=(--check)
fi

poetry run mypy "$@" "${flags[@]}" src  || exit 1

printf 'Mypy validation passed\n'
