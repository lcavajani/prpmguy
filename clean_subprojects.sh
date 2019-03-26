#!/usr/bin/env bash

USER=$1
REPOS=$(osc ls | grep home:$USER:test)

for r in $REPOS; do
    osc rdelete $r --recursive --force -m "cleaning"
done
