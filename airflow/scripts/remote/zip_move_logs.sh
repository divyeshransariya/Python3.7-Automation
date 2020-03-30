#!/bin/bash
set -euo pipefail

# $1    - which server
# $2    - port
# $3    - keyfile
# $4    - Remote Store Path
# $5    - remote drop path
# $6    - Run date
# $7... - Anything else on the grid (optional)

curr_date=$6
tgt_path="$4/outfiles/$curr_date/"

cd $tgt_path
if [ "$?" != "0" ]; then echo "Error (1)"; exit 1; fi

echo "Zipping log files"
numFiles1=$(find -type f | grep -e '\.log$' -e '_ToStrat' -e '_ToAdapt' -e 'json$' | grep -v '\.bz2$' | wc -l)
if [ "$?" != "0" ]; then echo "Error (2)"; exit 1; fi
echo "Found "$numFiles1" files to zip"
if [ "$numFiles1" != "0" ]; then
    find -type f | grep -e '\.log$' -e '_ToStrat' -e '_ToAdapt' -e 'json$' | grep -v '\.bz2$' | xargs bzip2
fi

echo "Finding Zipped Log Files"
numFiles2=$(find -type f | grep -e '\.log' -e '_ToStrat' -e '_ToAdapt' -e 'json' | grep '\.bz2$' | wc -l)
if [ "$?" != "0" ]; then echo "Error (3)"; exit 1; fi
echo "Found "$numFiles2" zipped files to copy"

if [ "$numFiles2" != "0" ]; then
    listFiles=$(find -type f | grep -e '\.log' -e '_ToStrat' -e '_ToAdapt' -e 'json' | grep '\.bz2$')
    if [ "$?" != "0" ]; then echo "Error (4)"; exit 1; fi

    echo "Found these files:"
    for FN in $listFiles
    do
        FP=$(dirname $FN)
        dropPath="/home/silver/ifs/drop_cloud/logs/$5/$FP"

        echo "Creating '"$dropPath"' on remote"
        mkdir -p $dropPath
        if [ "$?" != "0" ]; then echo "Error (5)"; exit 1; fi

        echo "coping '"$FN"' to Drop Location"
        cp $FN $dropPath/
        if [ "$?" != "0" ]; then echo "Error (6)"; exit 1; fi
    done
fi

exit 0
