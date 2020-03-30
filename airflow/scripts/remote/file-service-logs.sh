#!/usr/bin/env bash

# We allow failure in this script. Do not raise an alarm.
#set -euxo pipefail
set -ux

function do_xfer
{
    # Imagine is not there on the VPN. Hence we use the Public IP of the file-service server. This IP is pinned – it does
    # not change. See file-service.prism.md.
    #
    # When TaskChain is moved to the cloud, the IP address can be replaced with
    # file-service.vpn.slf which will resolve to a VPN-internal IP or
    # file-service.pub.slf which will resovle to the public IP
    
    # ssh -p 2222 root@13.228.245.51 "/src/file-service/pull-files.sh ${1}:/home/silver/ifs/drop_cloud/ keep/ --no-remove-source"
    /src/file-service/pull-files.sh ${1}:/home/silver/ifs/drop_cloud/ keep/ --no-remove-source
}

# Instead of specifying a list here, this could have been picked from the TaskChain grid. The problem is that
# downstream tasks depend on the completion of this task. Hence it cannot be run with a 'R' flag.
# TaskChain replacement can handle this better – no list here, specify on grid/tree/graph.

do_xfer "silver@imagine.kanjur.slf"
do_xfer "silver@kashmir.nse.slf"
do_xfer "silver@kashmir2.nse.slf"
do_xfer "silver@varun5.nse.slf"
do_xfer "silver@varun6.nse.slf"
do_xfer "silver@varun7.nse.slf"
do_xfer "silver@varun9.nse.slf"
do_xfer "silver@varun10.nse.slf"
do_xfer "silver@varun11.nse.slf"
do_xfer "silver@varun13.nse.slf"
do_xfer "silver@varun14.nse.slf"
do_xfer "silver@varun15.nse.slf"
do_xfer "silver@varun16.nse.slf"
do_xfer "silver@varun17.nse.slf"
do_xfer "silver@varun18.nse.slf"
do_xfer "silver@varunbse2.vpn.slf"
do_xfer "silver@valsons1.vpn.slf"

# This success exit is required for now so that taskchain proceeds if a single server fails
# When this task is moved to a taskchain replacement, the script should fail if the transfer fails
exit 0
