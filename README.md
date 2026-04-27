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
