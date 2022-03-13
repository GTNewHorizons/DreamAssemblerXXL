#!/usr/bin/env bash

flags=()
printf 'Running isort\n'
if [ -n "${CI}" ]; then
  flags=(--check)
fi

poetry run isort "$@" "${flags[@]}" src  || exit 1