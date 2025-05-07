#!/usr/bin/env bash

find "$1" -maxdepth 1 -name '*.md' -printf '%P\n' | sort -rV | head -n1