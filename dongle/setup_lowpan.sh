# specific for rpi node 04 used for boot
#!/bin/bash

ip link set wpan0 up
ip link add link wpan0 name lowpan0 type lowpan
ip link set lowpan0 up

iwpan phy phy0 set channel 0 24
ip link set lowpan0 down
ip link set wpan0 down
iwpan dev wpan0 set ackreq_default 1
iwpan dev wpan0 set short_addr 0x0004
iwpan dev wpan0 set pan_id 0x04D2
ip link set wpan0 up
ip link set lowpan0 up

sysctl -w net.ipv6.conf.lowpan0.forwarding=1
sysctl -w net.ipv6.conf.lowpan0.accept_ra=1

ip -6 addr add fd00::4/64 dev lowpan0
# generic manual version
# sudo ./setup_lowpan.sh
# #!/bin/bash

# ID=$1

# ip link set wpan0 up
# ip link add link wpan0 name lowpan0 type lowpan
# ip link set lowpan0 up

# iwpan phy phy0 set channel 0 24
# ip link set lowpan0 down
# ip link set wpan0 down
# iwpan dev wpan0 set ackreq_default 1
# iwpan dev wpan0 set short_addr 0x000$ID
# iwpan dev wpan0 set pan_id 0x04D2
# ip link set wpan0 up
# ip link set lowpan0 up

# sysctl -w net.ipv6.conf.lowpan0.forwarding=1
# sysctl -w net.ipv6.conf.lowpan0.accept_ra=1

# ip -6 addr add fd00::$ID/64 dev lowpan0
