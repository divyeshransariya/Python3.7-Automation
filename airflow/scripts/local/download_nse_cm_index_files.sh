#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path
# $4    - local store path
# $5    - Run date
if [ $# -gt 5 ]
then
    echo "Expect atleast 5 arguments (host, port, identity, storepath, execution_date)"
    echo "Provided: $*"
    exit 1
fi

host=$1
port=$2
identity_file=$3
if [[ ! $host =~ "@" ]]
then
   echo "Invalid host exiting!"
   exit 1
fi

# Shifting first three arguments
shift 3
echo "remaining arguments: $*"
today_date=$2
cd $1/$2

echo "File storage path = $1/$2"

# TODO: CM Security file download should move here too
# Why is it present on the FO ftp server?

############################
# Let's get BANKNIFTY files

echo "Working on fetching files for BANKNIFTY index"

bn_bod_filename=bod$(date +%Y%m%d -d $today_date).csv
bn_bod_filename_tgt=nse_cm_banknifty_bod_$today_date\.csv
bn_ts_filename_tgt=nse_cm_banknifty_ts_previous_$today_date\.csv
bn_cb_filename_tgt=nse_cm_banknifty_CB_$today_date\.zip

tgtDir=$1/$2/CBDIR

echo "bn_bod_filename : $bn_bod_filename"

if [[ -d "$tgtDir" || -f "$tgtDir" ]]; then
    if [ -d "ls -A $tgtDir" ];then
        echo "$tgtDir is already present! We'll try to look for files within it"
    else
        echo "$tgtDir is already present!"
        echo "Fetching files from $host"
        sftp -o port=$port -o IdentityFile=$identity_file $host:Nifty_Bank/NIFTY_BANK_$3.zip $tgtDir/
    fi
else
    mkdir $tgtDir

    # We could've checked the last downloaded file, but is it guaranteed that the
    # latest file will have the most recent timestamp?
    # For now, we just download all the files and check one by one which is to be used
    echo "Fetching files from $host"
    sftp -o port=$port -o IdentityFile=$identity_file $host:Nifty_Bank/NIFTY_BANK_$3.zip $tgtDir/
fi

# Temp dir to unzip each candidate file
tmpDir=$tgtDir/tmpDir
rm -rf $tmpDir

f=NIFTY_BANK_$3.zip
echo "Evaluating candidate file: $f"
src=$tgtDir/$f

# -q: Work quietly
# -j: Don't replicate zipfile directory structure while unzipping
# -d <dir>: Extract into <dir> directory
unzip -q -j -d $tmpDir $src

if [[ ! -f "$tmpDir/$bn_bod_filename" ]]; then
    rm -rf $tmpDir
    rm $src
    exit 1
fi

echo "Found matching candidate file: $f"

cntTS=`ls -1 $tmpDir/ts* | wc -l`
if [[ $cntTS -ne 1 ]]; then
    echo "$cntTS TS files found in archive $f!! Expected 1."
    exit 1
fi

tsFile=`ls -1 $tmpDir/ts*`

cp $src $1/$2/$bn_cb_filename_tgt
cp $tmpDir/$bn_bod_filename $1/$2/$bn_bod_filename_tgt
cp $tsFile $1/$2/$bn_ts_filename_tgt

rm -rf $tgtDir

echo "Downloaded BANKNIFTY BOD file for $today_date: $bn_bod_filename --> $bn_bod_filename_tgt"
echo "Downloaded BANKNIFTY TS file for $today_date: $tsFile --> $bn_ts_filename_tgt"

########################
# Let's get NIFTY files

echo "Working on fetching files for NIFTY index"

n_bod_filename=bod$(date +%Y%m%d -d $today_date).csv
n_bod_filename_tgt=nse_cm_nifty_bod_$today_date\.csv
n_ts_filename_tgt=nse_cm_nifty_ts_previous_$today_date\.csv
n_filename_tgt=nse_cm_nifty_$today_date\.zip

tgtDir=$1/$2/NDIR

if [[ -d "$tgtDir" || -f "$tgtDir" ]]; then
    if [ -d "ls -A $tgtDir" ];then
        echo "$tgtDir is already present! We'll try to look for files within it"
    else
        echo "$tgtDir is already present!"
        echo "Fetching files from $host"
        sftp -o port=$port -o IdentityFile=$identity_file $host:Nifty_50/NIFTY_50_$3.zip $tgtDir/
    fi
else
    mkdir $tgtDir

    # We could've checked the last downloaded file, but is it guaranteed that the
    # latest file will have the most recent timestamp?
    # For now, we just download all the files and check one by one which is to be used
    echo "Fetching files from $host"
    sftp -o port=$port -o IdentityFile=$identity_file $host:Nifty_50/NIFTY_50_$3.zip $tgtDir/
fi

# Temp dir to unzip each candidate file
tmpDir=$tgtDir/tmpDir
rm -rf $tmpDir

f=NIFTY_50_$3.zip

echo "Evaluating candidate file: $f"
src=$tgtDir/$f

# -q: Work quietly
# -j: Don't replicate zipfile directory structure while unzipping
# -d <dir>: Extract into <dir> directory
unzip -q -j -d $tmpDir $src

if [[ ! -f "$tmpDir/$n_bod_filename" ]]; then
    rm -rf $tmpDir
    rm $src
    exit 1
fi

echo "Found matching candidate file: $f"

cntTS=`ls -1 $tmpDir/ts* | wc -l`
if [[ $cntTS -ne 1 ]]; then
    echo "$cntTS TS files found in archive $f!! Expected 1."
    exit 1
fi

tsFile=`ls -1 $tmpDir/ts*`

cp $src $1/$2/$n_filename_tgt
cp $tmpDir/$n_bod_filename $1/$2/$n_bod_filename_tgt
cp $tsFile $1/$2/$n_ts_filename_tgt

rm -rf $tgtDir

echo "Downloaded NIFTY BOD file for $today_date: $n_bod_filename --> $n_bod_filename_tgt"
echo "Downloaded NIFTY TS file for $today_date: $tsFile --> $n_ts_filename_tgt"

echo "{ 'files' : ['$1/$2/$n_ts_filename_tgt','$1/$2/$n_bod_filename_tgt','$1/$2/$bn_ts_filename_tgt','$1/$2/$bn_bod_filename_tgt']}"

