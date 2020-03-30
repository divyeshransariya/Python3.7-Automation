#!/bin/bash
set -euo pipefail

# $1    - Local store path
# $2    - Run date

today_date=$2

echo "File storage path = "$1

file1in=$1/"nse_cm_security_"$today_date".csv"
file2in=$1/"nse_cm_banknifty_bod_"$today_date".csv"
file3in=$1/"nse_cm_banknifty_ts_previous_"$today_date".csv"
file4in=$1/"nse_cm_nifty_bod_"$today_date".csv"
file5in=$1/"nse_cm_nifty_ts_previous_"$today_date".csv"

file1out=$1/"nse_cm."$today_date".instruments"

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

echo "Generating CM instruments"
# Run program
# bin/dmd/debug/nse/cm/instruments_file_reader $file1in $file2in $file3in $file4in $file5in $file1out $today_date
bin/dmd/debug/nse/cm/instruments_file_reader $file1in $file2in $file3in $file4in $file5in $file1out $today_date

# Final output file exists check
if [[ ! -f "$file1out" ]]; then
    echo "File $file1out not found!"
    exit 1
fi

echo "CM Instruments finished processing."

echo "All files processed and verified... OK"
echo "{'files' : ['$file1out']}"