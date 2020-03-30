#!/bin/bash
set -euo pipefail

today_date=$1
exchange=$2
server=$3
deployPath=$4

instrumentList=(`find $deployPath/infiles/$today_date -name *.instruments`)

instFileString=""
for i in "${instrumentList[@]}"
do
    echo $i
    instFileString="$instFileString -i $i"
done

mmFile="$deployPath/outfiles/$today_date/$exchange""_UdpTbt_""$today_date.mmfile"

echo "exchange: $exchange"
echo "mmFile: $mmFile"
echo "server: $server"

runCmd="$deployPath/tools/bin/dmd/debug/blackbird/tools/metric/tbt_metric_statistics"
param="-n $exchange -s $server $instFileString -f $mmFile"

echo "Running command:"
echo -e "\t $runCmd $param"
set +e
$runCmd $param
if [ $? -ne 0 ]
then
    echo "tbt_metric_statistics Program Failed while processing $mmFile"
    exit 1
fi
set -e
