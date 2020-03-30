#!/bin/bash
set -euo pipefail

function graphiteIP()
{
	echo "localhost"
}

function graphitePort()
{
	echo "2003"
}

function getMetricPrefix()
{
	echo "Slf.Trading"
}

function appendTagToMetric()
{
    metric=$1
    tagName=$2
    tagVal=$3
    echo "$metric"";""$tagName""=""$tagVal"
}

function printMetricFormat()
{
    metricPath=$1
    value=$2
    dateToRun=$3
    offset=$4

    dateToSec="$dateToRun $offset"
    timeStamp=$(date -d "$dateToSec" +%s)

    metricFormat="$metricPath ""$value ""$timeStamp"
    echo "$metricFormat"
}
