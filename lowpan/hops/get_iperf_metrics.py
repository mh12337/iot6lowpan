#!/usr/bin/env python3
"""
Automate UDP iperf3 tests across bitrate and payload combinations.

Command template executed for each test:
iperf3 -c <destination_ipv6>%lowpan0 -p 5123 -u -b <bit_rate>k -l <payload_size> \
  --get-server-output -J > data_b<bit_rate>_l<payload_size>.json

Example:
python3 get_iperf_metrics.py fd00::8
"""

import argparse
import shlex
import subprocess
from pathlib import Path
import time
import sys

BITRATES_KBPS = [10, 30, 50, 60, 70, 80]
PAYLOAD_SIZES = [64, 96, 128, 256, 512, 1024]
INTERFACE = "lowpan0"
PORT = 5123
OUTPUT_DIR = "./results"
IPERF_BIN = "iperf3"
TEST_TIME = 30

MAX_RETRIES = sys.maxsize
RETRY_DELAY_SEC = 2


def run_iperf_test(
    destination_with_iface: str,
    bitrate_kbps: int,
    payload_size: int,
    outdir: Path,
	tcp: bool = False
) -> int:

    output_path = outdir / f"data_b{bitrate_kbps}_l{payload_size}_{'tcp' if tcp else 'udp'}.json"

    cmd = (
        f"{shlex.quote(IPERF_BIN)} "
        f"-c {shlex.quote(destination_with_iface)} "
        f"-p {PORT} "
	    f"{'-u ' if not tcp else ''}"
		f"-t {TEST_TIME} "
        f"-b {bitrate_kbps}k "
        f"-l {payload_size} "
        "--get-server-output -J "
        f"> {shlex.quote(str(output_path))}"
    )

    for attempt in range(1, MAX_RETRIES):

        print(
            f"Running test "
            f"(b={bitrate_kbps}k l={payload_size}) "
            f"[attempt {attempt}/{MAX_RETRIES}]"
        )

        completed = subprocess.run(
            cmd,
            shell=True,
            stderr=subprocess.PIPE,
            text=True,
        )

        if completed.returncode == 0:
            print(f"OK -> {output_path}")
            return 0

        print(
            f"FAILED attempt {attempt}: "
            f"{completed.stderr.strip()}"
        )

        if attempt < MAX_RETRIES:
            print(f"Retrying in {RETRY_DELAY_SEC}s...\n")
            time.sleep(RETRY_DELAY_SEC)

    print(
        f"GAVE UP after {MAX_RETRIES} attempts "
        f"(b={bitrate_kbps}k l={payload_size})"
    )

    return 1


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Run iperf3 tests over bitrate/payload matrix and save JSON outputs."
	)
	parser.add_argument("destination", help="Destination IPv6 address, e.g. fd00::8")
	parser.add_argument("--tcp", action="store_true", help="include tcp test")
	
	args = parser.parse_args()

	destination_with_iface = f"{args.destination}%{INTERFACE}"
	outdir = Path(OUTPUT_DIR)
	outdir.mkdir(parents=True, exist_ok=True)

	failures = 0
	total = len(BITRATES_KBPS) * len(PAYLOAD_SIZES)

	print(f"Destination: {destination_with_iface}")
	print(
		f"Tests: {total} ({len(BITRATES_KBPS)} bitrates x {len(PAYLOAD_SIZES)} payloads)"
	)
	print(f"Output dir: {outdir.resolve()}")

	for bitrate in BITRATES_KBPS:
		for payload in PAYLOAD_SIZES:
			rc = run_iperf_test(
				destination_with_iface=destination_with_iface,
				bitrate_kbps=bitrate,
				payload_size=payload,
				outdir=outdir,
			)
			if rc != 0:
				failures += 1
			time.sleep(2)
		
	if (args.tcp):
		for bitrate in BITRATES_KBPS:
			for payload in PAYLOAD_SIZES:
				rc = run_iperf_test(
				destination_with_iface=destination_with_iface,
				bitrate_kbps=bitrate,
				payload_size=payload,
				outdir=outdir,
				tcp=True
            )
			if rc!=0:
				failures += 1
			time.sleep(2)

	print(f"Finished: {total - failures}/{total} successful")
	return 0 if failures == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
