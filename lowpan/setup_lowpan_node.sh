#specific for rpi08
#!/bin/bash

ip link set wpan0 up
ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up

iwpan phy phy0 set channel 0 24
ip link set lowpan0 down
ip link set wpan0 down
iwpan dev wpan0 set ackreq_default 1
#comment in to use extended addr
#iwpan dev wpan0 set short_addr 0x0008
iwpan dev wpan0 set pan_id 0x04D2
ip link set wpan0 up
ip link set lowpan0 up

sysctl -w net.ipv6.conf.lowpan0.forwarding=1
sysctl -w net.ipv6.conf.lowpan0.accept_ra=1

#comment in to use extended addr
#ip -6 addr add fd00::8/64 dev lowpan0

sudo iwpan dev wpan0 associate pan_id 0x04d2 coord 0x0211223344556677
