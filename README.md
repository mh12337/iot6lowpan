# 6LoWPAN networking project
Group 1: Morten Husted, João Guedes Soares Vera, Pau Viñas Francisco, László Dávid Csávás	Csávás

## Hardware setup
Using rasbian lite 32 bit.
Use setup_lowan.sh

$ chmod +x setup_lowpan.sh
$ sudo cp setup_lowpan.sh /usr/local/bin/setup_lowpan.sh
$ sudo nano /etc/systemd/system/lowpan.service
Paste:
[Unit]
Description=Setup 6LoWPAN interface
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup_lowpan.sh
RemainAfterExit=true

[Install]
WantedBy=multi-user.target

$ sudo systemctl daemon-reexec
$ sudo systemctl daemon-reload
$ sudo systemctl enable lowpan.service

$ sudo reboot
