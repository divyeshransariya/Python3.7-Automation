#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path
# $4    - nse fo,cm,cd
# $5    - local scripts dir
# $6    - Remote Store Path

# Spliting first arg by delimeter '@' in order to get Host
IN=$1
host=(${IN//@/ })

source $5/upload_tbt_metrics.sh

upload_tbt_metrics $4 "${host[1]}" "$6" "$5"
