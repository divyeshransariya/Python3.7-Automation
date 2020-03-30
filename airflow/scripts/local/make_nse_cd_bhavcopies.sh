#!/bin/bash
set -euo pipefail

# $1    - Local logs dir
# $2    - Run date

today_date=$2

echo "File storage path = "$1

fileInstCD=$1/"nse_cd."$today_date".instruments"

fileBhavCDFut=$1/"nse_cd_fut_bhavcopy."$today_date".csv"
fileBhavCDOpt=$1/"nse_cd_opt_bhavcopy."$today_date".csv"
# fileBhavIrf=$1/"nse_irf_bhavcopy."$today_date".csv"

fileBhavCDOut=$1/"nse_cd."$today_date".bhavcopy"

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

# Make CD Bhavcopy
bin/dmd/debug/nse/cd/nse_cd_bhavcopy_reader $today_date $fileInstCD $fileBhavCDFut $fileBhavCDOpt $fileBhavCDOut
if [ "$?" == "0" ]; then
    echo "CD Bhavcopy generated successfully."
else
    echo "CD Bhavcopy generation FAILED!"
    exit 1
fi

# Final output file exists check
if [[ ! -f "$fileBhavCDOut" ]]; then
    echo "File $fileBhavCDOut not found!"
    exit 1
fi

echo "All files processed and verified... OK"

echo "{ 'files' : [ '$fileBhavCDOut' ] }"


