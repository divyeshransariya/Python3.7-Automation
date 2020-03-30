#!/bin/bash
set -euo pipefail

# $1    - Local logs dir
# $2    - Run date
today_date=$2

echo "File storage path = "$1

fileInstCM=$1/"nse_cm."$today_date".instruments"
fileInstFO=$1/"nse_fo."$today_date".instruments"

fileBhavCM=$1/"nse_cm_bhavcopy."$today_date".csv"
fileBhavFO=$1/"nse_fo_bhavcopy."$today_date".csv"

fileBhavCMOut=$1/"nse_cm."$today_date".bhavcopy"
fileBhavFOOut=$1/"nse_fo."$today_date".bhavcopy"

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

# Make CM Bhavcopy
bin/dmd/debug/nse/cm/nse_cm_bhavcopy_reader $today_date $fileInstCM $fileBhavCM $fileBhavCMOut
if [ "$?" == "0" ]; then
    echo "CM Bhavcopy generated successfully."
else
    echo "CM Bhavcopy generation FAILED!"
    exit 1
fi

bin/dmd/debug/nse/fo/nse_fo_bhavcopy_reader $today_date $fileInstCM $fileInstFO $fileBhavFO $fileBhavFOOut
if [ "$?" == "0" ]; then
    echo "FO Bhavcopy generated successfully."
else
    echo "FO Bhavcopy generation FAILED!"
    exit 1
fi

# Final output file exists check
if [[ ! -f "$fileBhavCMOut" ]]; then
    echo "File $fileBhavCMOut not found!"
    exit 1
fi

if [[ ! -f "$fileBhavFOOut" ]]; then
    echo "File $fileBhavFOOut not found!"
    exit 1
fi

echo "All files processed and verified... OK"

echo "{ 'files' : [ '$fileBhavCMOut' , '$fileBhavFOOut' ] }"

