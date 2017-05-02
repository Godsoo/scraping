#!/bin/sh

SCRAPY=$1

cd "${0%/*}"

echo "Precommit check for syntax and import errors"
eval $SCRAPY list > out.txt
rc=$?
if [ $rc != 0 ]
then
    echo "Commit Aborted! Found syntax or import errors"
    exit $rc
fi
