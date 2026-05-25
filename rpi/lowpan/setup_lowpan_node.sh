#specific for rpi08
#!/bin/bash

ip link set wpan0 up
ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up

iwpan phy phy0 set channel 0 24
ip link set lowpan0 down
ip link set wpan0 down
iwpan dev wpan0 set ackreq_default 1
iwpan dev wpan0 set short_addr 0xf208
iwpan dev wpan0 set pan_id 0x04D2
ip link set wpan0 up
ip link set lowpan0 up

#sysctl -w net.ipv6.conf.lowpan0.forwarding=1
sysctl -w net.ipv6.conf.lowpan0.accept_ra=2

ip -6 addr add fd00::8/64 dev lowpan0
ip -6 route add fd00::/64 dev lowpan0

sudo iwpan dev wpan0 associate pan_id 0x04d2 coord 0x0211223344556677

sudo ip -6 route add 2001:db8:1:ffff::/96 via fe80::11:2233:4455:6677 dev lowpan0
