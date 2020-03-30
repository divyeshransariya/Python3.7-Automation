#!/bin/bash
set -euo pipefail

# $1    - Hostname xyz@127.0.0.1
# $2    - Port
# $3    - identity file path

IN=$1
host=(${IN//@/ })

echo "Current server time = "$(ssh $1 "date")
echo "Will sync time at server "$1" to approx $(date)"
ssh $1 "date --set \"$(date)\""
echo "New server time = "$(ssh $1 "date")
