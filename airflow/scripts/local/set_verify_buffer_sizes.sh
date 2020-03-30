#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path
# $4    - Buff size

# Spliting first arg by delimeter '@' in order to get Host

desiredVal=$(($4 * 1024 * 1024))
if [ $desiredVal -gt 1048575 ]; then
    echo "Adjusting buffer sizes on server "$1" to "$desiredVal

    ssh $1 "sysctl -w net.core.rmem_max=$desiredVal"
    if [ "$?" != "0" ]; then
        echo "Got return code '$rv1' while setting rmem_max"
        exit 1
    fi

    ssh $1 "sysctl -w net.core.rmem_default=$desiredVal"
    if [ "$?" != "0" ]; then
        echo "Got return code '$rv2' while setting rmem_default"
        exit 1
    fi
    
    rMemMax=$(ssh $1 "cat /proc/sys/net/core/rmem_max")
    rMemDef=$(ssh $1 "cat /proc/sys/net/core/rmem_default")
    
    echo "rmem_max     value now is "$rMemMax
    echo "rmem_default value now is "$rMemDef

    if [ "$rMemMax" != "$desiredVal" ]; then
        echo "rmem_max didn't match desired value!"
        exit 1
    fi

    if [ "$rMemDef" != "$desiredVal" ]; then
        echo "rmem_default didn't match desired value!"
        exit 1
    fi

    echo "Buffer sizes verified - OK."
    exit 0
else
    echo "Could not compute a valid buffer size. I computed "$desiredVal" from input "$4
    exit 1
fi

