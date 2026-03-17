import argparse
from nrf802154_sniffer import Nrf802154Sniffer

def sniffa(dev, channel):
    sniffer = Nrf802154Sniffer()
    sniffer.extcap_capture(
        fifo="sniffa_file.pcap",
        dev=dev,
        channel=channel
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dev", help="Serial device - /dev/ttyACM3 or COM3")
    parser.add_argument("channel", type=int, help="802.15.4 channel")
    args = parser.parse_args()

    sniffa(args.dev, args.channel)

if __name__ == "__main__":
    main()