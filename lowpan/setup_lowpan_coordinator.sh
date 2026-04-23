#!/bin/bash

# delete default interface if it exists
iwpan dev wpan0 del 2>/dev/null || true

# create as coordinator with fixed ext_addr
sudo iwpan phy phy0 interface add wpan0 type coordinator 02:11:22:33:44:55:66:77

ip link set wpan0 up

iwpan phy phy0 set channel 0 24
ip link set wpan0 down
iwpan dev wpan0 set ackreq_default 1
iwpan dev wpan0 set short_addr 0x0002
iwpan dev wpan0 set pan_id 0x04D2
ip link set wpan0 up

ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up

sysctl -w net.ipv6.conf.lowpan0.forwarding=1
sysctl -w net.ipv6.conf.lowpan0.accept_ra=1
ip -6 addr add fd00::2/64 dev lowpan0