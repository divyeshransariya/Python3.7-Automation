#!/bin/bash
set -euo pipefail

# $1    - nse cm,fo,cd
# $2    - server
# $3    - Remote Store Path
# $4    - local scripts dir

function upload_tbt_metrics()
{
    source $4/common_metric.sh

    echo "Trying to run $3/scripts/generate_tbt_metrics.sh on $2"
    date=$(date +%Y-%m-%d)
    mmFile=$3/outfiles/$date/$1_UdpTbt_$date.mmfile_0
    if ssh $2 "stat $mmFile > /dev/null 2>&1"
    then
        output=`ssh $2 "bash $3/scripts/generate_tbt_metrics.sh $date $1 $2 $3" | grep "^Metric:"`
        echo "$output" | cut -c8-
        echo "$output" | cut -c8- | nc -d 2 $(graphiteIP) $(graphitePort)
    else
        echo "File $mmFile does not exist"
    fi
}

