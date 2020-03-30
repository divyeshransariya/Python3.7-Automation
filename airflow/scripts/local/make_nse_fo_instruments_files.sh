#!/bin/bash
set -euo pipefail

# $1    - Local store path
# $2    - Run date

today_date=$2

echo "File storage path = "$1

file1in=$1/"nse_fo_fo_contract_"$today_date".csv"
file2in=$1/"nse_fo_spd_contract_"$today_date".csv"
file3in=$1/"nse_fo_secban_"$today_date".csv"

# CM_instrument file location
file1out=$1/"nse_cm."$today_date".instruments"
# FO_instument file location
file2out=$1/"nse_fo."$today_date".instruments"

file1backup=$1/"nse_cm_cb_"$today_date".zip"

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

# CM instument file exists check
if [[ ! -f "$file1out" ]]; then
    echo "File $file1out not found!"
    exit 1
fi

echo "FO Instruments finished processing."
bin/dmd/debug/nse/cm/instruments_file_reader $file1out $file1in $file2in $file3in $file2out $today_date

if [[ ! -f "$file2out" ]]; then
    echo "File $file2out not found!"
    exit 1
fi

echo "FO Instruments FAILED processing!"
echo "All files processed and verified... OK"
echo "{'files' : ['$file1out']}"