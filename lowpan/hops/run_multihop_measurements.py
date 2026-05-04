#!/usr/bin/env python3
"""
run_multihop_measurements.py

Runs UDP iperf3 measurements for a two-hop / multi-hop 6LoWPAN scenario.

Typical topology:
  A = sender/client/router source, e.g. rpi02 = fd00::2
  B = intermediate/router,       e.g. rpi04 = fd00::4
  C = receiver/server,           e.g. rpi08 = fd00::8

Payload sizes:
  64, 128, 256, 512 bytes

Bitrates:
  10, 40, 80 kbps

Recommended use on A/rpi02:
  python3 run_multihop_measurements.py --server fd00::8 --via fd00::4

Requirements:
  - iperf3 server is running on receiver C/rpi08, e.g.:
      iperf3 -s -B fd00::8
  - IPv6 forwarding and routes are already configured so A reaches C via B.
  - This script does NOT configure the multi-hop routes. It only measures them.

Notes:
  - The script uses IPv6 explicitly with iperf3 -6.
  - Tests are ordered from lower offered load to higher offered load:
      all 10K tests, then all 40K tests, then all 80K tests.
  - Failed iperf3 JSON files with no intervals are recorded as connection/setup
    failures, not as zero-throughput measurements.
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


PAYLOAD_SIZES = [64, 128, 256, 512]
BITRATES_KBPS = [10, 40, 80]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_command(cmd, timeout: int) -> subprocess.CompletedProcess:
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )


def parse_iperf_json(json_text: str) -> Dict[str, Any]:
    """Parse iperf3 JSON. Handles both successful and error-only JSON output."""
    data = json.loads(json_text)

    result = {
        "iperf_error": data.get("error", ""),
        "connected_count": len(data.get("start", {}).get("connected", [])),
        "interval_count": len(data.get("intervals", [])),
        "throughput_kbps": None,
        "jitter_ms": None,
        "lost_packets": None,
        "packets": None,
        "lost_percent": None,
        "bytes": None,
    }

    end = data.get("end", {}) or {}

    # iperf3 UDP summaries are commonly under end["sum"]. Some versions may
    # also expose sum_received/sum_sent. Prefer receiver-side summary when present.
    summary = (
        end.get("sum_received")
        or end.get("sum")
        or end.get("sum_sent")
        or {}
    )

    bits_per_second = summary.get("bits_per_second")
    if bits_per_second is not None:
        result["throughput_kbps"] = bits_per_second / 1000.0

    result["jitter_ms"] = summary.get("jitter_ms")
    result["lost_packets"] = summary.get("lost_packets")
    result["packets"] = summary.get("packets")
    result["lost_percent"] = summary.get("lost_percent")
    result["bytes"] = summary.get("bytes")

    return result


def ping_check(address: str, interface: str = "", count: int = 2, timeout_s: int = 3) -> Tuple[bool, str, str]:
    cmd = ["ping", "-6"]
    if interface:
        cmd += ["-I", interface]
    cmd += ["-c", str(count), "-W", str(timeout_s), address]

    try:
        completed = run_command(cmd, timeout=max(10, count * timeout_s + 5))
        return completed.returncode == 0, completed.stdout, completed.stderr
    except Exception as exc:
        return False, "", repr(exc)


def save_command_output(outdir: Path, filename: str, cmd, timeout: int = 10) -> None:
    try:
        completed = run_command(cmd, timeout=timeout)
        text = (
            f"$ {' '.join(cmd)}\n"
            f"--- STDOUT ---\n{completed.stdout}\n"
            f"--- STDERR ---\n{completed.stderr}\n"
            f"--- RETURN CODE ---\n{completed.returncode}\n"
        )
    except Exception as exc:
        text = f"Failed to run {' '.join(cmd)}: {exc}\n"

    (outdir / filename).write_text(text, encoding="utf-8")


def save_snapshots(outdir: Path, interface: str, server: str, via: str = "") -> None:
    save_command_output(outdir, "ip_6_route_show.txt", ["ip", "-6", "route", "show"])
    save_command_output(outdir, "ip_6_addr_show.txt", ["ip", "-6", "addr", "show"])
    save_command_output(outdir, "ip_6_neigh_show.txt", ["ip", "-6", "neigh", "show", "dev", interface])
    save_command_output(outdir, "route_get_server.txt", ["ip", "-6", "route", "get", server])
    if via:
        save_command_output(outdir, "route_get_via.txt", ["ip", "-6", "route", "get", via])


def flush_neighbours(interface: str) -> None:
    # Requires passwordless sudo or an interactive sudo session.
    # If it fails, continue; the failure is not fatal for the measurement.
    try:
        completed = run_command(["sudo", "ip", "-6", "neigh", "flush", "dev", interface], timeout=10)
        if completed.returncode != 0:
            print("Warning: neighbour flush failed:", completed.stderr.strip(), file=sys.stderr)
    except Exception as exc:
        print(f"Warning: neighbour flush exception: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run two-hop / multi-hop 6LoWPAN iperf3 measurement matrix."
    )

    parser.add_argument(
        "--server",
        required=True,
        help="Receiver IPv6 address, e.g. fd00::8. For link-local use fe80::abcd%%lowpan0",
    )
    parser.add_argument(
        "--via",
        default="",
        help="Intermediate node IPv6 address, e.g. fd00::4. Used for ping/check metadata only.",
    )
    parser.add_argument(
        "--interface",
        default="lowpan0",
        help="Interface used for ping/neighbour snapshots. Default: lowpan0",
    )
    parser.add_argument(
        "--bind",
        default="",
        help="Optional local/source IPv6 address for iperf3 client, e.g. fd00::2",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5201,
        help="iperf3 server port. Default: 5201",
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
        default=15,
        help="Pause between tests in seconds. Default: 15",
    )
    parser.add_argument(
        "--high-rate-pause",
        type=int,
        default=30,
        help="Minimum pause after tests at or above 80 kbps. Default: 30",
    )
    parser.add_argument(
        "--outdir",
        default=f"results_multihop_{timestamp()}",
        help="Output directory",
    )
    parser.add_argument(
        "--iperf",
        default="iperf3",
        help="iperf3 executable path. Default: iperf3",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip initial ping checks and route snapshots",
    )
    parser.add_argument(
        "--pre-ping",
        action="store_true",
        help="Ping server before each test and mark test as precheck_failed if unreachable",
    )
    parser.add_argument(
        "--flush-neigh-on-fail",
        action="store_true",
        help="Run sudo ip -6 neigh flush dev INTERFACE after failed pre-ping or failed iperf run",
    )

    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not args.skip_checks:
        print("Saving initial route/address/neighbour snapshots...")
        save_snapshots(outdir, args.interface, args.server, args.via)

        if args.via:
            ok, stdout, stderr = ping_check(args.via, args.interface)
            (outdir / "initial_ping_via.txt").write_text(stdout + "\n--- STDERR ---\n" + stderr, encoding="utf-8")
            print(f"Initial ping to via ({args.via}): {'OK' if ok else 'FAILED'}")

        ok, stdout, stderr = ping_check(args.server, args.interface)
        (outdir / "initial_ping_server.txt").write_text(stdout + "\n--- STDERR ---\n" + stderr, encoding="utf-8")
        print(f"Initial ping to server ({args.server}): {'OK' if ok else 'FAILED'}")

    csv_path = outdir / "summary_multihop.csv"

    fieldnames = [
        "timestamp",
        "server",
        "via",
        "interface",
        "port",
        "payload_bytes",
        "bitrate_kbps",
        "repeat",
        "duration_s",
        "status",
        "success",
        "connected_count",
        "interval_count",
        "throughput_kbps",
        "jitter_ms",
        "lost_packets",
        "packets",
        "lost_percent",
        "bytes",
        "json_file",
        "stderr_file",
        "iperf_error",
        "error",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Reordered for stability: all low-rate tests first, then higher-rate tests.
        for bitrate in BITRATES_KBPS:
            for payload in PAYLOAD_SIZES:
                for repeat in range(1, args.repeats + 1):
                    test_time = timestamp()
                    bitrate_arg = f"{bitrate}K"

                    base_name = f"multihop_payload{payload}_rate{bitrate}kbps_repeat{repeat}_{test_time}"
                    json_filename = f"{base_name}.json"
                    stderr_filename = f"{base_name}.stderr.txt"
                    json_path = outdir / json_filename
                    stderr_path = outdir / stderr_filename

                    row = {
                        "timestamp": test_time,
                        "server": args.server,
                        "via": args.via,
                        "interface": args.interface,
                        "port": args.port,
                        "payload_bytes": payload,
                        "bitrate_kbps": bitrate,
                        "repeat": repeat,
                        "duration_s": args.duration,
                        "status": "not_started",
                        "success": False,
                        "connected_count": None,
                        "interval_count": None,
                        "throughput_kbps": None,
                        "jitter_ms": None,
                        "lost_packets": None,
                        "packets": None,
                        "lost_percent": None,
                        "bytes": None,
                        "json_file": json_filename,
                        "stderr_file": stderr_filename,
                        "iperf_error": "",
                        "error": "",
                    }

                    if args.pre_ping:
                        ok, ping_stdout, ping_stderr = ping_check(args.server, args.interface, count=1, timeout_s=3)
                        (outdir / f"{base_name}.pre_ping.txt").write_text(
                            ping_stdout + "\n--- STDERR ---\n" + ping_stderr,
                            encoding="utf-8",
                        )
                        if not ok:
                            row["status"] = "precheck_failed"
                            row["error"] = "Pre-test ping to server failed"
                            writer.writerow(row)
                            csvfile.flush()
                            print(f"Skipping test because pre-ping failed: payload={payload}B rate={bitrate}kbps")
                            if args.flush_neigh_on_fail:
                                flush_neighbours(args.interface)
                            time.sleep(max(args.pause, 5))
                            continue

                    cmd = [
                        args.iperf,
                        "-6",
                        "-c",
                        args.server,
                        "-p",
                        str(args.port),
                        "-u",
                        "-b",
                        bitrate_arg,
                        "-l",
                        str(payload),
                        "-t",
                        str(args.duration),
                        "-J",
                    ]

                    if args.bind:
                        cmd.extend(["-B", args.bind])

                    try:
                        completed = run_command(cmd, timeout=args.duration + 30)
                        json_path.write_text(completed.stdout, encoding="utf-8")
                        stderr_path.write_text(completed.stderr, encoding="utf-8")

                        parsed: Optional[Dict[str, Any]] = None
                        if completed.stdout.strip():
                            try:
                                parsed = parse_iperf_json(completed.stdout)
                                row.update(parsed)
                            except json.JSONDecodeError as exc:
                                row["error"] = f"JSONDecodeError: {exc}"

                        if completed.returncode == 0 and parsed and not parsed.get("iperf_error"):
                            row["status"] = "ok"
                            row["success"] = True
                            print(
                                f"OK: payload={payload}B, rate={bitrate}kbps, "
                                f"throughput={row['throughput_kbps']} kbps, "
                                f"jitter={row['jitter_ms']} ms, "
                                f"loss={row['lost_percent']}%"
                            )
                        else:
                            row["status"] = "iperf_failed"
                            if parsed and parsed.get("iperf_error"):
                                row["error"] = parsed.get("iperf_error", "")
                            elif completed.stderr.strip():
                                row["error"] = completed.stderr.strip()
                            elif not completed.stdout.strip():
                                row["error"] = "iperf3 returned non-zero and produced no stdout JSON"
                            print(f"iperf3 failed: {row['error']}", file=sys.stderr)
                            if args.flush_neigh_on_fail:
                                flush_neighbours(args.interface)

                    except subprocess.TimeoutExpired:
                        row["status"] = "timeout"
                        row["error"] = "TimeoutExpired"
                        stderr_path.write_text("TimeoutExpired\n", encoding="utf-8")
                        print("Test timed out", file=sys.stderr)
                        if args.flush_neigh_on_fail:
                            flush_neighbours(args.interface)

                    except Exception as exc:
                        row["status"] = "exception"
                        row["error"] = str(exc)
                        stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
                        print(f"Unexpected error: {exc}", file=sys.stderr)
                        if args.flush_neigh_on_fail:
                            flush_neighbours(args.interface)

                    writer.writerow(row)
                    csvfile.flush()

                    sleep_s = args.pause
                    if bitrate >= 80:
                        sleep_s = max(args.pause, args.high_rate_pause)
                    if sleep_s > 0:
                        time.sleep(sleep_s)

    if not args.skip_checks:
        print("Saving final route/address/neighbour snapshots...")
        final_dir = outdir / "final_snapshots"
        final_dir.mkdir(exist_ok=True)
        save_snapshots(final_dir, args.interface, args.server, args.via)

    print()
    print(f"Done. Results saved in: {outdir}")
    print(f"Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()
