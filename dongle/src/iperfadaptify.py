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
    summary = data["end"]["sum"]
    recv_summary = data["end"]["sum_received"]
    cpuutil = data["end"]["cpu_utilization_percent"]
    result = {
        "device_info": deviceinfo,
        "stamp": timestamp,
        "local_host": connection["local_host"],
        "remote_host": connection["remote_host"],
        "protocol": testinfo["protocol"],
        "num_streams:": testinfo["num_streams"],
        "blksize": testinfo["blksize"],
        "duration": testinfo["duration"],
        "target_bitrate": testinfo["target_bitrate"],
        "interval": testinfo["interval"],
        #data
        "bits_per_second": summary["bits_per_second"],
        "bitrate_kbps": summary["bits_per_second"] / 1000,
        "jitter_ms": summary["jitter_ms"],
        "total_packets": summary["packets"],
        "lost_packets": summary["lost_packets"],
        "lost_percent": summary["lost_percent"],
        "goodput": recv_summary["bits_per_second"] / 1000,
        "recv_bits_per_second": recv_summary["bits_per_second"],
        "out_of_order": data["end"]["streams"][0]["udp"]["out_of_order"],
        "pps": float, #placeholder

        #cpu util
        "cpu_host_total": cpuutil["host_total"],
        "cpu_host_user": cpuutil["host_user"],
        "cpu_host_system": cpuutil["host_system"],

        "cpu_remote_total": cpuutil["remote_total"],
        "cpu_remote_user": cpuutil["remote_user"],
        "cpu_remote_system": cpuutil["remote_system"],

    }

    return result


def stats(data):
    if len(data) == 0:
        return None, None, None
    mean = sum(data)/len(data)
    ma = max(data)
    std = statistics.stdev(data)
    return mean, ma, std

def get_time_series_data(data):
    times = []
    bitrates = []
    pps = []
    for interval in data["intervals"]:
        t = interval["sum"]["end"]        
        b = interval["sum"]["bits_per_second"] / 1000  
        
        packets = interval["sum"]["packets"]
        seconds = interval["sum"]["seconds"]

        prate = packets / seconds

        pps.append(prate)
        times.append(t)
        bitrates.append(b)

    return times, bitrates, pps


# extracts jitter, loss and throughput values from --get-server-output 
def extract_from_server_output(data):
    text = data.get("server_output_text", "")
    if text == "":
        return ([], []), ([], []), ([], [])
    jitters = []
    loss_pct = []
    bitrates = []
    ltimes = []
    jtimes = []
    btimes = []
    jitterPattern = re.compile(
        r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?([\d.]+)\s+ms"
    )
    lostpctPattern = re.compile(
        r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?\(([\d.]+)%\)"
    )
    tpPattern = re.compile(
         r"\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec.*?([\d.]+)\s+([KMG])bits/sec"
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
    
def do_table(metrics_list, multirun: bool):

    # group by blksize/payload size and target bitrate
    groups = defaultdict(list)

    for m in metrics_list:
        key = (m["blksize"], m["target_bitrate"])
        groups[key].append(m)

    table = []

    for (blksize, bitrate), entries in groups.items():
        
        n = len(entries)
        if n > 1 and not multirun:
            print(f"\n! obs: multiple tests ({n}) is made with payload size: {blksize} and target bitrate {bitrate}... if this is not a mistake, run script with flag --m . last input file, which was plotted, is also used for this table")

        if multirun:
            avg_throughput_sender = sum(e["bitrate_kbps"] for e in entries) / n
            avg_throughput_receiver = sum(e["goodput"] for e in entries) / n
            avg_jitter = sum(e["jitter_ms"] for e in entries) / n
            avg_loss = sum(e["lost_percent"] for e in entries) / n
            pps_avg = sum(e["pps"] for e in entries) / n
        else:
            e = entries.pop()
            avg_throughput_sender = e["bitrate_kbps"]
            avg_throughput_receiver = e["goodput"]
            avg_jitter = e["jitter_ms"]
            avg_loss = e["lost_percent"]
            pps_avg = e["pps"]

        table.append({
            "blksize": blksize,
            "target_bitrate": bitrate,
            "avg_throughput_sender": avg_throughput_sender,
            "avg_throughput_receiver": avg_throughput_receiver,
            "avg_jitter_ms": avg_jitter,
            "avg_loss_percent": avg_loss,
            "runs": n,
            "pps": pps_avg
        })

    table.sort(key=lambda x: (x["target_bitrate"], x["blksize"])) 

    # column widths
    w_ps = 12
    w_tb = 14
    w_s  = 14
    w_r  = 14
    w_j  = 10
    w_l  = 10
    w_n  = 6
    w_p  = 12

    print("\n=== Summary table of all tests ===")

    header = (
        f"{'Packet size':>{w_ps}} | "
        f"{'Target kbps':>{w_tb}} | "
        f"{'Sender kbps':>{w_s}} | "
        f"{'Receiver kbps':>{w_r}} | "
        f"{'Jitter (ms)':>{w_j}} | "
        f"{'Loss (%)':>{w_l}} | "
        f"{'Runs':>{w_n}} | "
        f"{'Avg. Packets/s':>{w_p}}"
    )

    print(header)
    print("-" * len(header))

    for row in table:
        print(
            f"{row['blksize']:>{w_ps}} | "
            f"{row['target_bitrate']:>{w_tb}} | "
            f"{row['avg_throughput_sender']:>{w_s}.2f} | "
            f"{row['avg_throughput_receiver']:>{w_r}.2f} | "
            f"{row['avg_jitter_ms']:>{w_j}.3f} | "
            f"{row['avg_loss_percent']:>{w_l}.2f} | "
            f"{row['runs']:>{w_n}} | "
            f"{row['pps']:>{w_p}.2f}"
        )
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

            #stamp = metrics["stamp"]
            #stamp = datetime.datetime.fromtimestamp(stamp).strftime("%d%m%Y-%H%M%S")
            # get #intervals, and interval bitrates, pps
            times, bitrates, ppsd = get_time_series_data(data)
            pps_mean, pps_max_, pps_std = stats(ppsd)
            metrics["pps"] = pps_mean
            metricsAll.append(metrics)
            (_, jitters), (ltimes, lost_pct), (btimes, recv_bitrates) = extract_from_server_output(data)
            # previous logic removed the last 2 elements of jitter/loss/recv lists; keep that behavior
            # but ensure all series have the same length before plotting to avoid matplotlib shape errors
            jit_trim = jitters[:-2] if len(jitters) > 2 else jitters[:]
            lost_trim = lost_pct[:-2] if len(lost_pct) > 2 else lost_pct[:]
            recv_trim = recv_bitrates[:-2] if len(recv_bitrates) > 2 else recv_bitrates[:]

            n = min(len(times), len(bitrates), len(jit_trim), len(lost_trim), len(recv_trim), len(ppsd))
            if n == 0:
                print("Skipping plot cycle due to missing data after alignment")
            else:
                times_plot = times[:n]
                bitrates_plot = bitrates[:n]
                jitters_plot = jit_trim[:n]
                lost_plot = lost_trim[:n]
                recv_plot = recv_trim[:n]
                pps_plot = ppsd[:n]

                do_plots(times_plot, bitrates_plot, jitters_plot, lost_plot, recv_plot, metrics["bits_per_second"], metrics["recv_bits_per_second"],
                         metrics["blksize"], metrics["target_bitrate"], pps_plot, "", args.pltshow)

            if jitters:
                print(f"Final jitter estimate: {jitters[-1]}")
            
            
    print("\n[*] Generating bar charts...")
    do_barcharts(metricsAll, args.pltshow)
    do_table(metricsAll, args.m)
