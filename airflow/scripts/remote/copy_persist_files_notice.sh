#!/bin/bash
set -euo pipefail

# $1    - Remote Store Path

persistNoticePath="/home/silver/tmp/PersistFile_1Day_Notice"

echo "Checking for persist path"
set +e
cd $1/localpersist/
if [ "$?" != "0" ]; then echo "Directory $1/localpersist/ doesn't exist, so nothing to copy. Done here!"; exit 0; fi
set -e

echo "persist path : $(pwd) "
echo "Finding persist files"
numFiles1=$(ls *.localpersist | wc -l)
if [ "$?" != "0" ]; then echo "Error (2)"; exit 1; fi
echo "Found "$numFiles1" persist files to copy"

if [ "$numFiles1" != "0" ]; then
    echo "Clearing previous persist files in 1Day Notice"
    if [ -d '$persistNoticePath' ]; then rm -rf $persistNoticePath; fi
    if [ "$?" != "0" ]; then echo "Error (0)"; exit 1; fi

    listFiles=$(ls *.localpersist)
    if [ "$?" != "0" ]; then echo "Error (4)"; exit 1; fi

    echo "Creating '"$persistNoticePath"' on remote"
    mkdir -p $persistNoticePath
    if [ "$?" != "0" ]; then echo "Error (5)"; exit 1; fi

    echo "Found these files:"
    for FN in $listFiles
    do
        echo "Copying '"$FN"' to Drop Location"
        cp $FN $persistNoticePath/
        if [ "$?" != "0" ]; then echo "Error (6)"; exit 1; fi
    done

    echo "Last copied on: $($date +%T)" > $persistNoticePath/last_copied.log
fi

exit 0
