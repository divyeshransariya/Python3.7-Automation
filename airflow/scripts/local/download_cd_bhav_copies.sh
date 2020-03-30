#!/bin/bash
#set -euo pipefail

# $1    - host URL(https://example.com)
# $2    - Source file or endpoint(/file_path/file_name)
# $3    - file name
# $4    - future output file name
# $5    - option output file name 
# $6    - CD_unzipped_future_bhav_filename
# $7    - CD_unzipped_option_bhav_filename
# $8    - Local logs dir
# $9    - run date
# $10    - anything else on grid

today_date=$6

curr_year=$(date -d "$today_date" +%Y)
curr_month=$(date -d "$today_date" +%b)
curr_month=${curr_month^^}
curr_day=$(date -d "$today_date" +%d)
curr_date=$(date -d "$today_date" +%d%m%y)

cd $8

echo "File storage path = "$8

cd_bhav_path="http://www.nseindia.com/archives/cd/bhav/"
cd_bhav_filename="CD_Bhavcopy$curr_date"

CD_unzipped_future_bhav_filename="CD_NSE_FO"$curr_date
CD_unzipped_option_bhav_filename="CD_NSE_OP"$curr_date
dbf_suffix=".dbf"
csv_suffix=".csv"
zip_suffix=".zip"

cd_fu_bhav_name_out="nse_cd_fut_bhavcopy.$today_date.csv"
cd_op_bhav_name_out="nse_cd_opt_bhavcopy.$today_date.csv"

# Download and rename CD file
wget -U firefox $1$2$zip_suffix
unzip $3$zip_suffix
dos2unix $6$csv_suffix
dos2unix $7$csv_suffix
mv $6$csv_suffix $4
mv $7$csv_suffix $5

echo "{ 'files' : ['$(pwd)/$4' , '$(pwd)/$5'] }"
# # Download and rename IRF file
# wget -U firefox $1$irf_bhav_filename$csv_suffix
# dos2unix $irf_bhav_filename$csv_suffix
# mv $irf_bhav_filename$csv_suffix $irf_bhav_name_out
