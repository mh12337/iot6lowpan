#!/bin/bash
tayga --mktun

ip link set nat64 up
ip addr add 2001:db8:1::1 dev nat64  # router's IPv6 address
ip addr add 192.168.0.1 dev nat64    # router's IPv4 address
ip route add 2001:db8:1:ffff::/96 dev nat64  # from tayga.conf
ip route add 192.168.255.0/24 dev nat64      # from tayga.conf

ip6tables -A FORWARD -i lowpan0 -o nat64 -j ACCEPT
ip6tables -A FORWARD -i nat64 -o lowpan0 -j ACCEPT
iptables -t nat -A POSTROUTING -s 192.168.255.0/24 -j MASQUERADE # masquerade traffic from dynamic pool to the internet

sudo sysctl -w net.ipv4.ip_forward=1
sudo sysctl -w net.ipv6.conf.all.forwarding=1

tayga