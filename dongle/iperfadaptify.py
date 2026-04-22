import json
import matplotlib.pyplot as plt
import openpyxl
from openpyxl import Workbook
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
        "packet_loss_percent": summary["lost_percent"],
        "total_packets": summary["packets"],
        #cpu util
        "cpu_host_total": cpuutil["host_total"],
        "cpu_host_user": cpuutil["host_user"],
        "cpu_host_system": cpuutil["host_system"],

        "cpu_remote_total": cpuutil["remote_total"],
        "cpu_remote_user": cpuutil["remote_user"],
        "cpu_remote_system": cpuutil["remote_system"],

    }

    return result

def get_time_series_data(data):
    times = []
    bitrates = []

    for interval in data["intervals"]:
        t = interval["sum"]["end"]        
        b = interval["sum"]["bits_per_second"] / 1000  

        times.append(t)
        bitrates.append(b)

    return times, bitrates
def save_to_excel(metrics, times, bitrates):
    stamp = metrics["stamp"]
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

def do_plots(times, bitrates, jitters, lost_percents):
    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    plt.plot(times, bitrates)
    plt.xlabel("Time (s)")
    plt.ylabel("Bitrate (kbps)")
    plt.title("Throughput over time")
    plt.grid()

    # plt.subplot(3, 1, 2)
    # plt.plot(times, jitters)
    # plt.xlabel("Time (s)")
    # plt.ylabel("Jitter (ms)")
    # plt.title("Jitter over time")
    # plt.grid()

    # plt.subplot(3, 1, 3)
    # plt.plot(times, lost_percents)
    # plt.xlabel("Time (s)")
    # plt.ylabel("Packet Loss (%)")
    # plt.title("Packet Loss over time")
    # plt.grid()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    data = get_data("results.json")
    metrics = extract_iperf_metrics(data)
    times, bitrates = get_time_series_data(data)
    save_to_excel(metrics, times, bitrates)
    do_plots(times, bitrates, [], [])
    print("=== Iperf Results ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")