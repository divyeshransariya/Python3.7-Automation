#!/bin/bash
set -euo pipefail

# $1    - host URL(https://example.com)
# $2    - Source file or endpoint(/file_path/file_name)
# $3    - output file(s) name
# $4    - Local store path
# $5    - Run date

cd $4/$5

echo "File storage path = $4/$5"

if [ $# -lt 5 ];then
    echo """
    Invalid args:$*
    Usage:
    <script_path>/download_linux_file_from_url.sh <URL> <source_file> <output_file> <local_store_path> <Run Date>
    """
    exit 1
fi

# Download, unzip and rename fo file
wget -U firefox -O $3 $1$2
dos2unix $3

# In order to push File path in airflow's Xcom
echo "{ 'files' : ['$(pwd)/$3'] }"