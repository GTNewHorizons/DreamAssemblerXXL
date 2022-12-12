#!/usr/bin/env bash

printf 'Running linter\n'

poetry run flake8 "$@" --docstring-convention numpy --config flake8.ini src || exit 1
