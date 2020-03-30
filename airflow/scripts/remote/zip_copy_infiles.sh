#!/bin/bash
set -euo pipefail

# $1    - Remote Store Path

echo "Checking for infiles path"
cd $1/infiles/
if [ "$?" != "0" ]; then echo "Error (1)"; exit 1; fi

echo "Checking for deploy_store"
cd /home/silver/deploy_store/
if [ "$?" != "0" ]; then echo "Error (2)"; exit 1; fi

echo "Checking for ifs drop local"
cd /home/silver/ifs/drop_local/
if [ "$?" != "0" ]; then echo "Error (3)"; exit 1; fi

echo "Checking if there are files"
numFiles=$(cd $1/infiles/ ; ls | wc -l)
if [ "$?" != "0" ]; then echo "Error (4)"; exit 1; fi

if [ "$numFiles" == "0" ]; then
    echo "No files... OK"
    exit 0
fi

echo $numFiles" files to copy..."

echo "Making drop local infiles folder"
mkdir -p /home/silver/ifs/drop_local/infiles/
if [ "$?" != "0" ]; then echo "Error (5)"; exit 1; fi

echo "Copying to ifs local drop"
cd $1/infiles/ ; cp -n -r --no-preserve=links --no-dereference * /home/silver/ifs/drop_local/infiles/
if [ "$?" != "0" ]; then echo "Error (6)"; exit 1; fi

rm -f /home/silver/ifs/drop_local/infiles/today
if [ "$?" != "0" ]; then echo "Error (7)"; exit 1; fi

echo "Making deploy store infiles folder"
mkdir -p /home/silver/deploy_store/infiles/
if [ "$?" != "0" ]; then echo "Error (8)"; exit 1; fi

echo "Moving to deploy_store"
cd $1/infiles/ ; mv * /home/silver/deploy_store/infiles/
if [ "$?" != "0" ]; then echo "Error (9)"; exit 1; fi

exit 0