#!/bin/bash
set -euo pipefail

# $1    - Hostname localhost@127.0.0.1
# $2    - Port
# $3    - identity file path
# $4    - Local store Path
# $5    - Remote store Path
echo "Will rsync: $1 -> $4:$5/"
rsync -avzI $4 $1:$5/

