# 6LoWPAN networking project
Group 1: Morten Husted, João Guedes Soares Vera, Pau Viñas Francisco, László Dávid Csávás	Csávás

## Hardware setup
### RPI setup
SD is flashed with a rasbian lite 32 bit image, using Raspberry Pi Imager. <br>
There was a mismatch between the standard device tree for the at86rf233 device and the device driver for at86rf230. The sleep pin was set as active low in the device tree, and the SLP_TR pin is active high [[1]](https://ww1.microchip.com/downloads/en/devicedoc/doc5131.pdf). The driver sets the sleep pin to low during initialization [[2]](https://github.com/torvalds/linux/blob/b4e07588e743c989499ca24d49e752c074924a9a/drivers/net/ieee802154/at86rf230.c#L1550) - this logical low was being interpreted as a physical high on the pin causing a probing error:
```
[   73.813174] at86rf230 spi0.0: Detected at86rf233 chip version 1
[   73.817186] at86rf230 spi0.0: unexcept state change from 0x00 to 0x08. Actual state: 0x00
[   73.856560] at86rf230 spi0.0: DVDD error
[   73.856632] at86rf230 spi0.0: probe with driver at86rf230 failed with error -22
```
To fix this, we decompiled the dtbo file, changed the sleep pin to be active high, and recompiled it to at86rf233-fixed.dtbo using 
```
sudo dtc -@ -I dts -O dtb \
  -o /boot/firmware/overlays/at86rf233-fixed.dtbo \
at86rf233-overlay.dts
```
/boot/firmware/config.txt is then updated to use this overlay, with SPI clock speed = 0.5MHz:

```
dtparam=spi=on
dtoverlay=at86rf233-fixed,speed=500000
```
### nRF52840 dongle setup
The nRF52840 dongle is setup with firmware from [nodicsemi](https://github.com/nordicsemi/nRF-Sniffer-for-802.15.4/tree/master) (specifically [nrf802154_sniffer_nrf52840dongle.hex](https://github.com/mh12337/iot6lowpan/blob/main/dongle/nrf802154_sniffer_nrf52840dongle.hex)). We also use the [python wrapper](https://github.com/nordicsemi/nRF-Sniffer-for-802.15.4/blob/master/nrf802154_sniffer/nrf802154_sniffer.py). Our [sniffa.py](https://github.com/mh12337/iot6lowpan/blob/main/dongle/sniffa.py) uses this wrapper and simply takes the COM port used by the dongle and the radio channel to sniff, as console arguments and specifies the file name where the results should be written to.
### 6LowPAN setup
Use [setup_lowpan_node.sh](https://github.com/mh12337/iot6lowpan/blob/main/lowpan/setup_lowpan_node.sh) on node and [setup_lowpan_coordinator.sh](https://github.com/mh12337/iot6lowpan/blob/main/lowpan/setup_lowpan_coordinator.sh) on coordinator <br> 
[iwpan-tools v0.10](https://github.com/linux-wpan/wpan-tools/releases) is needed to configure from user space <br>
Make the script executable and enable it to run on boot
```bash
chmod +x setup_lowpan.sh
sudo cp setup_lowpan.sh /usr/local/bin/setup_lowpan.sh
sudo nano /etc/systemd/system/lowpan.service
```

Paste:

```ini
[Unit]
Description=Setup 6LoWPAN interface
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup_lowpan.sh
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
```
Save file <br>
Run:
```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable lowpan.service

sudo reboot
```
Should now be setup, check with 'ip a'

# NAT64 Interface
To enable communication to IPv4 adresses in the internet, a NAT64 interface had to be created in the border router (coordinator node).
This can be done with Tayga, this [guide](https://github.com/apalrd/tayga/blob/main/docs/README.md) was used to help setup the interface.

## Tayga Installation and Configuration
The first step is to install tayga, which can be done with:
```bash
git clone git@github.com:apalrd/tayga.git
cd tayga
make
```
Now, to make dynamic mapping persistent to tayga restarts, we need to create a directory, where a dynamic.map file will be stored.
```bash
mkdir -p /var/db/tayga
```
Dynamic mapping is the way in which IPv6 adresses in our network will be mapped to IPv4 adressess, that devices from outside our network will use to communicate back to devices in our system. This translation is done as necessary, when a device from our network sends a message to an IPv4 destination, tayga will assign it an IPv4 adress taken from a dynamic pool. This dynamic pool specifies a range of ip adressess that can be used for this mapping. This is configured later.

The next step is to create a configuration file for tayga, a very simple one was created, that you can see [here](https://github.com/mh12337/iot6lowpan/blob/main/tayga/tayga.conf) and placed in /etc/ directory
For more information on each of the fields, refer to [this](https://github.com/apalrd/tayga/blob/main/tayga.conf.example) example config.

We now need to change the routing setup on the system to send IPv4 and IPv6 packets to tayga. This is done via a list of commands that we have place in [this](https://github.com/mh12337/iot6lowpan/blob/main/tayga/tayga_setup.sh) shell script. And comprises of creating a TUN interface for tayga and setting up the ip adressess and routes for that interface, routing our IPv6 prefix and IPv4 dynamic pool adressess to it. We also need to create a masquerade for the dynamic pool adressess, since this pool only contains private adressess, this will make it so that outgoing packages are sent under the gateway's public ip address. IPv4 and IPv6 forwarding also needs to be enabled. The script fishished by running Tayga, everything should be in order after this.

Finally, before getting communiaction working from leaf node, to the internet, we need to add some routing configuration on our leaf nodes:

```bash
sudo ip -6 route add 2001:db8:1:ffff::/96 via fe80::11:2233:4455:6677 dev lowpan0 #route NAT64 prefixed addresses to the router nodes link address
```

To make the NAT64 Interface plug and play we added a system services that runs the tayga setup script as a daemon on startup, after the lowpan service:
```bash
chmod +x tayga_setup.sh
sudo cp tayga_setup.sh /usr/local/bin/tayga_setup.sh
sudo nano /etc/systemd/system/tayga.service
```
paste:
```bash
[Unit]
Description=TAYGA NAT64 Setup
After=network-online.target lowpan.service
Wants=network-online.target
Requires=lowpan.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/tayga_setup.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```
Save file <br>
Run:
```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable tayga.service

sudo reboot
```

