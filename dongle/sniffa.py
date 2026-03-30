import argparse
import time
from nrf802154_sniffer import Nrf802154Sniffer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dev", help="Serial device - /dev/ttyACM3 or COM3")
    parser.add_argument("channel", type=int, help="802.15.4 channel")
    args = parser.parse_args()

    sniffer = Nrf802154Sniffer()
    sniffer.start_threaded(
        fifo="sniffa_file.pcap",
        dev=args.dev,
        channel=args.channel
    )

    print("Sniffing... Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping sniffer...")
        sniffer.stop_thread()
        print("Stopped.")

if __name__ == "__main__":
    main()