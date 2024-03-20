#!/usr/bin/env bash

unset -v latest
for file in "$1"/*; do
    [[ $file -nt $latest ]] && latest=$(basename "$file" .md)
done

echo $latest