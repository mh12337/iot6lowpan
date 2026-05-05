#!/usr/bin/env python3
"""
run_singlehop_measurements.py

Runs UDP iperf3 measurements for the single-hop 6LoWPAN scenario.

Scenario:
A = sender/client, e.g. rpi02 = fd00::2
C = receiver/server, e.g. rpi08 = fd00::8

Payload sizes:
64, 128, 256, 512 bytes

Bitrates:
10, 40, 80 kbps

Usage on sender node:
python3 run_singlehop_measurements.py --server fd00::8

Requirements:
- iperf3 server must be running on receiver node first:
  iperf3 -s
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


PAYLOAD_SIZES = [64, 128, 256, 512]
BITRATES_KBPS = [10, 40, 80]


def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_command(cmd, timeout):
    print("Running:", " ".join(cmd), flush=True)

    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )

    return completed


def main():
    parser = argparse.ArgumentParser(
        description="Run single-hop 6LoWPAN iperf3 measurement matrix."
    )

    parser.add_argument(
        "--server",
        required=True,
        help="Receiver IPv6 address, e.g. fd00::8. For link-local use fe80::abcd%%lowpan0",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds. Default: 30",
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of repeats per matrix point. Default: 1",
    )

    parser.add_argument(
        "--pause",
        type=int,
        default=10,
        help="Pause between tests in seconds. Default: 10",
    )

    parser.add_argument(
        "--outdir",
        default=f"results_singlehop_{timestamp()}",
        help="Output directory",
    )

    parser.add_argument(
        "--iperf",
        default="iperf3",
        help="iperf3 executable path. Default: iperf3",
    )

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "summary_singlehop.csv"

    with csv_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for bitrate  in BITRATES_KBPS:
            for payload in PAYLOAD_SIZES:
                for repeat in range(1, args.repeats + 1):
                    test_time = timestamp()
                    bitrate_arg = f"{bitrate}K"

                    json_filename = (
                        f"singlehop_payload{payload}_rate{bitrate}kbps_"
                        f"repeat{repeat}_{test_time}.json"
                    )
                    json_path = outdir / json_filename

                    cmd = [
                        args.iperf,
                        "-6",
			            "-c",
                        args.server,
                        "-u",
                        "-b",
                        bitrate_arg,
                        "-l",
                        str(payload),
                        "-t",
                        str(args.duration),
                        "-J",
                    ]

                    row = {
                        "timestamp": test_time,
                        "server": args.server,
                        "payload_bytes": payload,
                        "bitrate_kbps": bitrate,
                        "repeat": repeat,
                        "duration_s": args.duration,
                        "success": False,
                        "throughput_kbps": None,
                        "jitter_ms": None,
                        "lost_packets": None,
                        "packets": None,
                        "lost_percent": None,
                        "bytes": None,
                        "json_file": json_filename,
                        "error": "",
                    }

                    try:
                        completed = run_command(cmd, timeout=args.duration + 20)
                        json_path.write_text(completed.stdout)

                        if completed.returncode != 0:
                            row["error"] = completed.stderr.strip()
                            print("iperf3 failed:", row["error"], file=sys.stderr)
                        else:
                            metrics = parse_iperf_json(completed.stdout)
                            row.update(metrics)
                            row["success"] = True

                            print(
                                f"OK: payload={payload}B, "
                                f"rate={bitrate}kbps, "
                                f"throughput={row['throughput_kbps']} kbps, "
                                f"jitter={row['jitter_ms']} ms, "
                                f"loss={row['lost_percent']}%"
                            )

                    except subprocess.TimeoutExpired:
                        row["error"] = "TimeoutExpired"
                        print("Test timed out", file=sys.stderr)

                    except json.JSONDecodeError as exc:
                        row["error"] = f"JSONDecodeError: {exc}"
                        print("Could not parse iperf3 JSON", file=sys.stderr)

                    except Exception as exc:
                        row["error"] = str(exc)
                        print(f"Unexpected error: {exc}", file=sys.stderr)

                    writer.writerow(row)
                    csvfile.flush()

                    if args.pause > 0:
			if bitrate >= 80:
				time.sleep(max(args.pause, 30))
			else:
                time.sleep(args.pause)

    print()
    print(f"Done. Results saved in: {outdir}")
    print(f"Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()
