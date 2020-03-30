#!/usr/bin/env bash

# $1    - which server
# $2    - port
# $3    - keyfile

# We allow failure in this script. Do not raise an alarm.
#set -euxo pipefail
set -eux

# Imagine is not there on the VPN. Hence we use the Public IP of the file-service server. This IP is pinned – it does
# not change. See file-service.prism.md.
#
# When TaskChain is moved to the cloud, the IP address can be replaced with
# file-service.vpn.slf which will resolve to a VPN-internal IP or
# file-service.pub.slf which will resovle to the public IP

# ssh -p 2222 root@13.228.245.51 "/src/file-service/pull-files.sh silver@imagine.kanjur.slf:/home/silver/ifs/drop_local/ ifs/ --remove-source"
/src/file-service/pull-files.sh silver@imagine.kanjur.slf:/home/silver/ifs/drop_local/ ifs/ --remove-source