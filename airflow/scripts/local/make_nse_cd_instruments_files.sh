#!/bin/bash
set -euo pipefail

# $1    - Local store path
# $2    - Run date

today_date=$2

echo "File storage path = "$1

file1in=$1/"nse_cd_fo_contract_"$today_date".csv"
file2in=$1/"nse_cd_spd_contract_"$today_date".csv"

file1out=$1/"nse_cd."$today_date".instruments"
file2out=$1/"nse_cd."$today_date".extrainfo"

if [[ ! -d "$INFRA_REPO_PATH" ]]; then
    echo "Infra repo path $INFRA_REPO_PATH not found!"
    exit 1
fi

cd $INFRA_REPO_PATH/../nse/
if [ "$?" == "0" ]; then
    echo "Currently at NSE repo folder "$(pwd)
else
    echo "NSE Repo not found!"
    exit 1
fi

# Run programs
bin/dmd/debug/nse/cd/instruments_file_reader $file1in $file2in $file1out $file2out $today_date
if [ "$?" == "0" ]; then
    echo "CD Instruments finished processing."
else
    echo "CD Instruments FAILED processing!"
    exit 1
fi

# Final output file exists check
if [[ ! -f "$file1out" ]]; then
    echo "File $file1out not found!"
    exit 1
fi

echo "All files processed and verified... OK"
echo "{'files' : ['$file1out']}"
