# performs automated analysis on iperf data from json files, each specifying a specific test with different payload size and bitrate, in a specified directory
# creates plots and charts of relevant metrics and saves them to a file
# creates tables with every metric for each test

import json
import datetime
import matplotlib.pyplot as plt
from openpyxl import Workbook
import re
import os
import argparse
import statistics
import numpy as np
from collections import defaultdict
from pathlib import Path

metricsAll = []
fileName = "placeholder"
saveDir = "./iperf-analysis"

def get_data(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data
def extract_iperf_metrics(data):
    
    deviceinfo = data["start"]["system_info"]
    connection = data["start"]["connected"][0]
    timestamp = data["start"]["timestamp"]["timesecs"]
    testinfo = data["start"]["test_start"]
    is_tcp = testinfo["protocol"] == "TCP"
    if is_tcp:
        summary = data["end"]["sum_sent"]
    else:
        summary = data["end"]["sum"]
    recv_summary = data["end"]["sum_received"]
    cpuutil = data["end"]["cpu_utilization_percent"]
    result = {
        "device_info": deviceinfo,
        "stamp": timestamp,
        "local_host": connection["local_host"],
        "remote_host": connection["remote_host"],
        "protocol": testinfo["protocol"],
        "num_streams": testinfo["num_streams"],
        "blksize": testinfo["blksize"],
        "duration": testinfo["duration"],
        "target_bitrate": testinfo["target_bitrate"],
        "interval": testinfo["interval"],
        "bits_per_second": summary["bits_per_second"],
        "bitrate_kbps": summary["bits_per_second"] / 1000,
        "goodput": recv_summary["bits_per_second"] / 1000,
        "recv_bits_per_second": recv_summary["bits_per_second"],
        "cpu_host_total": cpuutil["host_total"],
        "cpu_host_user": cpuutil["host_user"],
        "cpu_host_system": cpuutil["host_system"],
        "cpu_remote_total": cpuutil["remote_total"],
        "cpu_remote_user": cpuutil["remote_user"],
        "cpu_remote_system": cpuutil["remote_system"],
        "pps": float,
        "protocol": testinfo["protocol"]
    }

    if is_tcp:
        sender = data["end"]["streams"][0]["sender"]
        result["retransmits"]  = summary.get("retransmits", 0)
        result["mean_rtt_us"]  = sender.get("mean_rtt", 0)
        result["max_rtt_us"]   = sender.get("max_rtt", 0)
        result["min_rtt_us"]   = sender.get("min_rtt", 0)
        # set neutral defaults so the rest of the pipeline doesn't crash
        result["jitter_ms"]    = 0.0
        result["total_packets"] = 0
        result["lost_packets"]  = 0
        result["lost_percent"]  = 0.0
        result["out_of_order"]  = 0
    else:
        result["jitter_ms"]    = summary["jitter_ms"]
        result["total_packets"] = summary["packets"]
        result["lost_packets"]  = summary["lost_packets"]
        result["lost_percent"]  = summary["lost_percent"]
        result["out_of_order"]  = data["end"]["streams"][0]["udp"]["out_of_order"]
    return result


def stats(data):
    if len(data) == 0:
        return None, None, None
    mean = sum(data)/len(data)
    ma = max(data)
    std = statistics.stdev(data)
    return mean, ma, std

def get_time_series_data(data, skip=False):
    times = []
    bitrates = []
    pps = []
    for interval in data["intervals"]:
        t = interval["sum"]["end"]        
        b = interval["sum"]["bits_per_second"] / 1000  
        
        if not skip:
            packets = interval["sum"]["packets"]
            seconds = interval["sum"]["seconds"]

            prate = packets / seconds

            pps.append(prate)
        else:
            pps.append(0)
        times.append(t)
        bitrates.append(b)

    return times, bitrates, pps


# extracts jitter, loss and throughput values from --get-server-output 
def extract_from_server_output(data, skip=False):
    text = data.get("server_output_text", "")
    if text == "":
        return ([], []), ([], []), ([], [])
    jitters = []
    loss_pct = []
    bitrates = []
    ltimes = []
    jtimes = []
    btimes = []
    if not skip:
        jitterPattern = re.compile(
            r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?([\d.]+)\s+ms"
        )
        lostpctPattern = re.compile(
            r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?\(([\d.]+)%\)"
        )
        for match in jitterPattern.finditer(text):
            start = float(match.group(1))
            end = float(match.group(2))
            jitter = float(match.group(3))
            jtimes.append(end)
            jitters.append(jitter)
        for match in lostpctPattern.finditer(text):
            end = float(match.group(2))
            loss = float(match.group(3))

            ltimes.append(end)
            loss_pct.append(loss)
    tpPattern = re.compile(
         r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?([\d.]+)\s+([KMG])bits/sec"
    )

   
    for match in tpPattern.finditer(text):
        end = float(match.group(2))
        value = float(match.group(3))
        unit = match.group(4)

        if unit == "K":
            b = value
        else:
            print("!!! Unit of server throughput is not KBPS !!!")

        btimes.append(end)
        bitrates.append(b)

    return (jtimes, jitters), (ltimes, loss_pct), (btimes, bitrates)

def save_to_excel(metrics, times, bitrates, stamp=None):
    if stamp is None:
        stamp = datetime.datetime.fromtimestamp(stamp).strftime("%d%m%Y-%H%M%S")
       
    filename = f"results-{stamp}.xlsx"

    wb = Workbook()

    # Sheet 1: Summary
    ws1 = wb.active
    ws1.title = "summary"

    ws1.append(["Metric", "Value"])
    for k, v in metrics.items():
        ws1.append([k, v])

    # Sheet 2: Time series
    ws2 = wb.create_sheet(title="time_series")
    ws2.append(["time_s", "bitrate_kbps"])

    for t, b in zip(times, bitrates):
        ws2.append([t, b])

    wb.save(filename)
    print(f"Saved to {filename}")

def do_plots(times, bitrates, jitters, lost_percents, recv_bitrates, bavg, ravg, size, tb, ppsd, stamp=None, show=False):
    n = min(len(times),len(bitrates),len(jitters),len(lost_percents),len(recv_bitrates),len(ppsd))
    if n == 0:
        print("Skipping plot cycle due to missing data")
        return

    fig, axs = plt.subplots(4,1,figsize=(12, 10),sharex=True)   
    fig.suptitle(f"Network performance\nPayload size: {size} B | Target bitrate: {tb} kbps",fontsize=16)

    axs[0].plot(times, bitrates,label=f"Sender ({bavg/1000:.2f} kbps avg)")
    axs[0].plot(times, recv_bitrates, "--",label=f"Receiver ({ravg/1000:.2f} kbps avg)")
    axs[0].set_ylabel("kbps")
    axs[0].set_title("Throughput")
    axs[0].legend()
    axs[0].grid(alpha=0.3)

    axs[1].plot(times, jitters)
    axs[1].set_ylabel("ms")
    axs[1].set_title("Jitter")
    axs[1].grid(alpha=0.3)

    axs[2].plot(times, lost_percents)
    axs[2].set_ylabel("%")
    axs[2].set_title("Packet loss")
    axs[2].grid(alpha=0.3)

    axs[3].plot(times, ppsd)
    axs[3].set_ylabel("PPS")
    axs[3].set_title("Packets per second (PPS)")
    axs[3].set_xlabel("Time (s)")
    axs[3].grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    save_dir = Path(saveDir)
    save_dir.mkdir(parents=True, exist_ok=True)

    save_as = f"plots-{fileName}.png"
    save_path = save_dir / save_as

    plt.savefig(save_path, dpi=300)

    print(f" - Plot saved at {save_path}")

    if show:
        plt.show()
def do_plots_tcp(times, bitrates, recv_bitrates, bavg, ravg, size, tb, ppsd, stamp=None, show=False):
    print(bitrates)
    fig, axs = plt.subplots(2,1,figsize=(12, 10),sharex=True)   
    fig.suptitle(f"Network performance TCP\nPayload size: {size} B | Target bitrate: {tb} kbps",fontsize=16)
    axs[0].plot(times, bitrates,label=f"Sender ({bavg/1000:.2f} kbps avg)")
    axs[0].plot(times, recv_bitrates, "--",label=f"Receiver ({ravg/1000:.2f} kbps avg)")
    axs[0].set_ylabel("kbps")
    axs[0].set_title("Throughput")
    axs[0].legend()
    axs[0].grid(alpha=0.3)
    
    axs[1].plot(times, ppsd)
    axs[1].set_ylabel("PPS")
    axs[1].set_title("Packets per second (PPS)")
    axs[1].set_xlabel("Time (s)")
    axs[1].grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    save_dir = Path(saveDir)
    save_dir.mkdir(parents=True, exist_ok=True)

    save_as = f"plots-{fileName}.png"
    save_path = save_dir / save_as

    plt.savefig(save_path, dpi=300)

    print(f" - Plot saved at {save_path}")

    if show:
        plt.show()
def do_barcharts(metrics_list, show=False):
    filtered = [
        {
            "bitrate_kbps": m["bitrate_kbps"],
            "blksize": m["blksize"],
            "total_packets": m["total_packets"],
            "lost_packets": m["lost_packets"],
            "lost_percent": m["lost_percent"],
        }
        for m in metrics_list
    ]

    labels = [
        f"{m['bitrate_kbps']:.2f} kbps\n{m['blksize']} bytes"
        for m in filtered
    ]

    x = np.arange(len(filtered))
    width = 0.25

    total = [m["total_packets"] for m in filtered]
    lost = [m["lost_packets"] for m in filtered]
    lost_pct = [m["lost_percent"] for m in filtered]

    plt.figure(figsize=(12, 6))

    bars_total = plt.bar(x - width, total, width, label="Total")
    bars_lost = plt.bar(x, lost, width, label="Lost")
    bars_lost_pct = plt.bar(x + width, lost_pct, width, label="Lost %")

    plt.bar_label(bars_total, padding=3)
    plt.bar_label(bars_lost, padding=3)
    plt.bar_label(bars_lost_pct, padding=3)

    plt.xticks(x, labels)
    plt.xlabel("Test cases (Bitrate / Blksize)")
    plt.ylabel("Values")
    plt.title("Packet loss per test")
    plt.legend()

    plt.tight_layout()
    save_as = "barchart-results.png"
    save_dir = Path(saveDir)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / save_as
    plt.savefig(save_path)
    print(f" - Bar chart saved at {save_path}")
    if show:
        plt.show()
    
def _build_groups(metrics_list, multirun, keys):
    groups = defaultdict(list)
    for m in metrics_list:
        key = (m["blksize"], m["target_bitrate"])
        groups[key].append(m)

    table = []
    for (blksize, bitrate), entries in groups.items():
        n = len(entries)
        if n > 1 and not multirun:
            print(f"\n! obs: multiple tests ({n}) with payload size: {blksize} "
                  f"and target bitrate {bitrate}... run with --m if intentional")
        if multirun:
            row = {k: sum(e[k] for e in entries) / n for k in keys}
        else:
            e = entries[-1]
            row = {k: e[k] for k in keys}

        table.append({
            "blksize":                 blksize,
            "target_bitrate":          bitrate / 1000,
            "avg_throughput_sender":   row["bitrate_kbps"],
            "avg_throughput_receiver": row["goodput"],
            "avg_jitter_ms":           row.get("jitter_ms", 0.0),
            "avg_loss_percent":        row.get("lost_percent", 0.0),
            "pps":                     row.get("pps", 0.0),
            "total_p":                 row.get("total_packets", 0),
            "mean_rtt_ms":             row.get("mean_rtt_us", 0) / 1000,
        })

    table.sort(key=lambda x: (x["target_bitrate"], x["blksize"]))
    return table


UDP_KEYS = ["bitrate_kbps", "goodput", "jitter_ms", "lost_percent", "pps", "total_packets"]
TCP_KEYS = ["bitrate_kbps", "goodput", "mean_rtt_us"]


def _print_udp_table(metrics_list, multirun):
    table = _build_groups(metrics_list, multirun, UDP_KEYS)
    w_ps, w_tb, w_s, w_r, w_j, w_l, w_p, w_tp = 12, 14, 14, 14, 10, 10, 12, 12

    print("\n=== UDP Summary ===")
    header = (f"{'Packet size':>{w_ps}} | {'Target kbps':>{w_tb}} | "
              f"{'Sender kbps':>{w_s}} | {'Receiver kbps':>{w_r}} | "
              f"{'Jitter (ms)':>{w_j}} | {'Loss (%)':>{w_l}} | "
              f"{'Avg. Packets/s':>{w_p}} | {'Total packets':>{w_tp}}")
    print(header)
    print("-" * len(header))
    for row in table:
        print(f"{row['blksize']:>{w_ps}} | {row['target_bitrate']:>{w_tb}} | "
              f"{row['avg_throughput_sender']:>{w_s}.2f} | "
              f"{row['avg_throughput_receiver']:>{w_r}.2f} | "
              f"{row['avg_jitter_ms']:>{w_j}.3f} | "
              f"{row['avg_loss_percent']:>{w_l}.2f} | "
              f"{row['pps']:>{w_p}.2f} | "
              f"{row['total_p']:>{w_tp}.2f}")


def _print_tcp_table(metrics_list, multirun):
    table = _build_groups(metrics_list, multirun, TCP_KEYS)
    w_ps, w_tb, w_s, w_r, w_rtt = 12, 14, 14, 14, 14

    print("\n=== TCP Summary ===")
    header = (f"{'Packet size':>{w_ps}} | {'Target kbps':>{w_tb}} | "
              f"{'Sender kbps':>{w_s}} | {'Receiver kbps':>{w_r}} | "
              f"{'Mean RTT (ms)':>{w_rtt}}")
    print(header)
    print("-" * len(header))
    for row in table:
        print(f"{row['blksize']:>{w_ps}} | {row['target_bitrate']:>{w_tb}} | "
              f"{row['avg_throughput_sender']:>{w_s}.2f} | "
              f"{row['avg_throughput_receiver']:>{w_r}.2f} | "
              f"{row['mean_rtt_ms']:>{w_rtt}.3f}")


def do_table(metrics_list, multirun: bool):
    udp_metrics = [m for m in metrics_list if m["protocol"] == "UDP"]
    tcp_metrics = [m for m in metrics_list if m["protocol"] == "TCP"]
    if udp_metrics:
        _print_udp_table(udp_metrics, multirun)
    if tcp_metrics:
        _print_tcp_table(tcp_metrics, multirun)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="iperf Analyzer")
    parser.add_argument(
        "directory",
        default=".",
        help="Path to data"
    )
    parser.add_argument(
        "--pltshow",
        action="store_true",
        help="Show plots / save only"
    )
    parser.add_argument(
        "--m",
        action="store_true",
        help="Folder contains more runs with same configs"
    )

    args = parser.parse_args()
    directory = args.directory
  
    pps = []
    for fn in os.listdir(directory):
        if fn.endswith(".json"):
            filepath = os.path.join(directory, fn)
            fileName = fn.removesuffix(".json")
            print(f"\n[*] Processing: {filepath}")

            data = get_data(filepath)
            metrics = extract_iperf_metrics(data)
            is_tcp = metrics["protocol"] == "TCP"

            #stamp = metrics["stamp"]
            #stamp = datetime.datetime.fromtimestamp(stamp).strftime("%d%m%Y-%H%M%S")
            # get #intervals, and interval bitrates, pps
            times, bitrates, ppsd = get_time_series_data(data, is_tcp)
            pps_mean, pps_max_, pps_std = stats(ppsd)
            metrics["pps"] = pps_mean
            metricsAll.append(metrics)
            (_, jitters), (ltimes, lost_pct), (btimes, recv_bitrates) = extract_from_server_output(data, is_tcp)
            # previous logic removed the last 2 elements of jitter/loss/recv lists; keep that behavior
            # but ensure all series have the same length before plotting to avoid matplotlib shape errors
            jit_trim = jitters[:-2] if len(jitters) > 2 else jitters[:]
            lost_trim = lost_pct[:-2] if len(lost_pct) > 2 else lost_pct[:]
            recv_trim = recv_bitrates[:-2] if len(recv_bitrates) > 2 else recv_bitrates[:]

            if is_tcp:
                n = min(len(times), len(bitrates), len(ppsd))
                if n == 0:
                    print("Skipping TCP plot cycle due to missing data after alignment")
                else:
                    times_plot   = times[:n]
                    bitrates_plot = bitrates[:n]
                    pps_plot     = ppsd[:n]
                    # recv from server output if available, otherwise mirror sender
                    recv_plot    = recv_trim[:n] if len(recv_trim) >= n else bitrates_plot

                    do_plots_tcp(times_plot, bitrates_plot, recv_plot,
                                metrics["bits_per_second"], metrics["recv_bits_per_second"],
                                metrics["blksize"], metrics["target_bitrate"],
                                pps_plot, "", args.pltshow)
            else:
                n = min(len(times), len(bitrates), len(jit_trim), len(lost_trim), len(recv_trim), len(ppsd))
                if n == 0:
                    print("Skipping plot cycle due to missing data after alignment")
                else:
                    times_plot    = times[:n]
                    bitrates_plot = bitrates[:n]
                    jitters_plot  = jit_trim[:n]
                    lost_plot     = lost_trim[:n]
                    recv_plot     = recv_trim[:n]
                    pps_plot      = ppsd[:n]

                    do_plots(times_plot, bitrates_plot, jitters_plot, lost_plot, recv_plot,
                            metrics["bits_per_second"], metrics["recv_bits_per_second"],
                            metrics["blksize"], metrics["target_bitrate"],
                            pps_plot, "", args.pltshow)

                if jitters:
                    print(f"Final jitter estimate: {jitters[-1]}")
            
            
    print("\n[*] Generating bar charts...")
    #do_barcharts(metricsAll, args.pltshow)
    do_table(metricsAll, args.m)