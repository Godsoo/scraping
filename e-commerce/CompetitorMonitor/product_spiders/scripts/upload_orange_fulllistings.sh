#!/bin/bash

PYTHON=~/pythoncrawlers/bin/python

cd "$( dirname "$0" )"

SITES=( '100001' '100002' '100003' '100004' '100005' '100006' )

for site_id in "${SITES[@]}"; do
    ${PYTHON} uploadfulllistingwebsite.py ${site_id} all
done