#!/bin/sh

PYTHON=~/pythoncrawlers/bin/python

cd "$( dirname "$0" )"

if [ $1 = "crawl" ]; then
    echo "Running the crawl manager"
    $PYTHON crawl.py
elif [ $1 = "schedule" ]; then
    echo "Running the schedule manager"
    $PYTHON schedule.py
elif [ $1 = "upload" ]; then
    echo "Running the upload manager"
    $PYTHON upload.py
fi
    