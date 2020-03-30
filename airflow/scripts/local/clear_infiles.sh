#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path
# $4    - Remote Store Path

# Spliting first arg by delimeter '@' in order to get Host
IN=$1
host=(${IN//@/ })

echo "Checking for infiles path"
ssh ${host[1]} "cd $4/infiles/"
if [ "$?" != "0" ]; then echo "Error (1)"; exit 1; fi

echo "Checking if there are files"
numFiles=$(ssh ${host[1]} "cd $4/infiles/ ; ls | wc -l")
if [ "$?" != "0" ]; then echo "Error (2)"; exit 1; fi

if [ "$numFiles" == "0" ]; then
    echo "No files... OK"
    exit 0
fi

echo "Removing infiles"
ssh ${host[1]} "cd $4/infiles/ ; rm -rf $4/infiles/*"
if [ "$?" != "0" ]; then echo "Error (3)"; exit 1; fi

exit 0
