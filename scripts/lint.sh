#!/usr/bin/env bash

printf 'Running linter\n'

poetry run flake8 "$@" --config flake8.ini src || exit 1
