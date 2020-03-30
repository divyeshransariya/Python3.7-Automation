#!/bin/bash
set -euo pipefail

# $1    - store path
# $2    - taskName
# $3    - onload parameter (= yesOnload or noOnload)
# $4    - date
# $5+   - command string

if [ $# -lt 5 ]
then
    echo "Expect atleast 5 arguments (path, taskName, onloadParam, commandString)"
    echo "Provided: $*"
    exit 1
fi

storePath=$1
taskName=$2
onloadParam=$3
date=$4

# Remove these params so that we're only left with the program command to run
shift 4
origCommand="$*"
execPath=$1
execName=${execPath##*/}
onloadPrefix=""

this_date=$(date +%Y-%m-%d)
OutFileTempl="$taskName"_"$this_date"
OutFile="$OutFileTempl"_"$(date +%T).log"
OutDir="$storePath/outfiles/$date"
OutFileFullPath="$OutDir/$OutFile"
OutFileFullPathTempl="$OutDir/$OutFileTempl"

echo "Running program: $taskName"
echo "Executable     : $execPath"
echo "Output file    : $OutFileFullPath"

hasOnload=0
set +e
onload=$(which onload > /dev/null 2>&1)
if [ "$?" == "0" ]; then
    hasOnload=1
fi
set -e

if [ "$hasOnload" == "1" ]
then
    echo "Onload         : Present"
    if [ "$onloadParam" = "yesOnload" ]; then
        onloadPrefix="onload -p latency"
        echo "Onload         : Spin Mode"
    elif [ "$onloadParam" = "yesOnloadPoll" ]; then
        onloadPrefix="onload"
        echo "Onload         : Poll Mode"
    else
        echo "Onload         : Not required"
    fi
else
    echo "Onload         : Not present"
fi

echo

# Check if OutDir exists
if [ ! -d $OutDir ]
then
    echo "FAILURE: Output directory $OutDir does not exist!"
    exit 1
fi

##check if cgroup exists and cgexec works by firing a dummy ls command
cpusetName=sf_critical
if cgexec -g cpuset:${cpusetName} ls>/dev/null 2>&1; then
    cgexecParam="cgexec -g cpuset:${cpusetName}"
    echo "cgexec available, will run with cgroups"
else
    cgexecParam=""
    echo "cgexec not available, will run without cgroups"
fi

echo "Running command:"
echo 
echo "BLACKBIRD_CFG_APPNAME=$execName $cgexecParam $onloadPrefix stdbuf -oL $origCommand > "$OutFileFullPathTempl'_$(date +%T).log  2>&1'
echo 
BLACKBIRD_CFG_APPNAME=$execName $cgexecParam $onloadPrefix stdbuf -oL $origCommand > $OutFileFullPath 2>&1
