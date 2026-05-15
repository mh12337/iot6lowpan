#!/usr/bin/env python3
"""
Automate TCP iperf3 tests across bitrate and payload combinations.

Command template executed for each test:
iperf3 -c <destination_ipv6>%lowpan0 -p 5123 -b <bit_rate>k -l <payload_size> \
  --get-server-output -J > data_tcp_b<bit_rate>_l<payload_size>.json

Example:
python3 test_tcp.py fd00::8
"""

import argparse
import shlex
import subprocess
import time
from pathlib import Path


BITRATES_KBPS = [10, 40, 80]
PAYLOAD_SIZES = [64, 128, 256, 512]
INTERFACE = "lowpan0"
PORT = 5123
OUTPUT_DIR = "."
IPERF_BIN = "iperf3"


def run_iperf_test(
	destination_with_iface: str,
	bitrate_kbps: int,
	duration: int,
	outdir: Path,
) -> int:
	output_path = outdir / f"data_tcp_b{bitrate_kbps}_l{payload_size}.json"

	cmd = (
		f"{shlex.quote(IPERF_BIN)} "
		f"-c {shlex.quote(destination_with_iface)} "
		f"-p {PORT} "
		f"-b {bitrate_kbps}k "
		f"-l {payload_size} "
		f"-t {duration} "
		"--get-server-output -J "
		f"> {shlex.quote(str(output_path))}"
	)

	print(f"Running: {cmd}")
	completed = subprocess.run(cmd, shell=True, stderr=subprocess.PIPE, text=True)

	if completed.returncode != 0:
		print(
			f"FAILED TCP b={bitrate_kbps}k l={payload_size}: {completed.stderr.strip()}"
		)
	else:
		print(f"OK -> {output_path}")

	return completed.returncode


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Run TCP iperf3 tests over bitrate/payload matrix and save JSON outputs."
	)
	parser.add_argument("destination", help="Destination IPv6 address, e.g. fd00::8")
	parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds. Default: 30")
	parser.add_argument("--pause", type=int, default=10, help="Pause between tests in seconds. Default: 10")

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
				duration=args.duration,
				outdir=outdir,
			)
			if rc != 0:
				failures += 1
			
			if args.pause > 0:
				# Si el bitrate és alt, podem donar una mica més de temps de recuperació a la xarxa, tal com es feia a l'altre script
				if bitrate >= 80:
					time.sleep(max(args.pause, 30))
				else:
					time.sleep(args.pause)

	print(f"Finished: {total - failures}/{total} successful")
	return 0 if failures == 0 else 1


if __name__ == "__main__":
	raise SystemExit(main())
