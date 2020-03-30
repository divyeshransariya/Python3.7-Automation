#!/bin/bash
set -euxo pipefail

# $1    - exchange prefix in format
            # 10.42.6
            # 13.251.124

# Expects the user to provide the MTBT/TAP NIC and allowed FO TAP server as $2
# $2    - Anything else on the grid (optional)
            # it must contain format in which first should be iterface and second latency like
            #  eth0,29
            #  enp4s0,ANY
            #  eth2,RAND
            #  eth0,NONE

# FIXME this script needs to be made idempotent

IN=$2
arr=(${IN//,/ })
arrlen=${#arr[@]}

if [ $arrlen -ne 2 ]
then
    echo "Expected TAP/MTBT interface name and rx-usecs interrupt latency allowed for interface. Provided: $2"
    exit 1
fi

tapMTbtNIC=${arr[0]}
rxUsecLat=${arr[1]}
echo "# Input param: $IN"
echo "# TAP and MTBT NIC interface: $tapMTbtNIC"
echo "# RX/TX Interrupt latency: $rxUsecLat"
echo

echo "# Verifying $tapMTbtNIC exists on server and has IP in range $1.*"
val=$(ifconfig $tapMTbtNIC | grep $1)
if [ "$val" == "" ]
then
    echo "host does not have interface named $tapMTbtNIC"
    exit 1
fi
echo "# Verified"
echo

# Should this use ip route or ifconfig (deprecated)?
# Should this setup the interface and the routes or only the routes?

route add -host 10.30.1.13 dev $tapMTbtNIC
echo "# Setting up route to exchange side switch"
echo

route add -net 172.18.0.0 netmask 255.255.0.0 gw 10.30.1.13 dev $tapMTbtNIC
echo "# Setting up route to exchange gateway"
echo

route add -net 172.19.0.0 netmask 255.255.0.0 gw 10.30.1.13 dev $tapMTbtNIC
echo "# Setting up route to exchange gateway"
echo

route add -net 172.22.0.0 netmask 255.255.0.0 gw 10.30.1.13 dev $tapMTbtNIC
echo "# Setting up route to exchange gateway"
echo

route add -net 172.28.124.0 netmask 255.255.255.0 gw 10.30.1.13 dev $tapMTbtNIC
echo "# Setting up route to TBT fetch servers"
echo

arp -s 10.30.1.13 58:f3:9c:81:2b:bc
echo "# Adding arp entry for exchange switch"
echo

ethtool -C $tapMTbtNIC adaptive-rx off
echo

ethtool -C $tapMTbtNIC  rx-usecs $rxUsecLat tx-usecs $rxUsecLat
echo


set +e
ethtool -K $tapMTbtNIC gro off lro off gso off tso off
set -e
echo

sysctl -w net.ipv4.tcp_timestamps=0
echo

sysctl -w net.ipv4.tcp_low_latency=1
echo
