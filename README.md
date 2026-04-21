# 6LoWPAN networking project
Group 1: Morten Husted, João Guedes Soares Vera, Pau Viñas Francisco, László Dávid Csávás	Csávás

## Hardware setup
### Device setup
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
/boot/firmware/config.txt is then updated to use this overlay, with SPI clock speed = 1MHz
### 6LowPAN setup
Use setup_lowan.sh
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

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable lowpan.service

sudo reboot
```
