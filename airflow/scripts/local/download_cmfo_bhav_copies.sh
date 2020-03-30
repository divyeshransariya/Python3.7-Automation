#!/bin/bash
#set -euo pipefail

# $1    - host URL(https://example.com)
# $2    - Source file or endpoint(/file_path/file_name)
# $3    - file name
# $4    - output file(s) name
# $5    - Local logs dir
# $6    - run date
# $7    - anything else on grid

today_date=$6

curr_year=$(date -d "$today_date" +%Y)
curr_month=$(date -d "$today_date" +%b)
curr_month=${curr_month^^}
curr_day=$(date -d "$today_date" +%d)
curr_date=$(date -d "$today_date" +%d%m%y)

cd $5

echo "File storage path = "$5
zip_suffix=".zip"

# Download, unzip and rename CM file
wget -U firefox $1$2$zip_suffix
unzip $3$zip_suffix
dos2unix $3
mv $3 $4

echo "{ 'files' : ['$(pwd)/$4'] }"
