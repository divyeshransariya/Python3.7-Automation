#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path

# Spliting first arg by delimeter '@' in order to get Host


ssh $1 "ls"

if [  "$?" == "0" ]; then
    set +e
    ssh $1 "reboot" 
    set -e
    exit 0
else
    exit 1
fi

