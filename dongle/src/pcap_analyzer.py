import subprocess
from unittest import result
import pandas as pd
from io import StringIO
import matplotlib.pyplot as plt
import argparse

def run_tshark(pcap_file="sniffa_file.pcap"):
    # might need modification!!! 
    cmd = [
    r"C:\Program Files\Wireshark\tshark.exe",
    "-r", pcap_file,
    "-T", "fields",

    # Frame
    "-e", "frame.number",
    "-e", "frame.time_epoch",
    "-e", "frame.len",
    "-e", "_ws.col.Protocol",

    # IPv6
    "-e", "ipv6.src",
    "-e", "ipv6.dst",

    # MAC
    "-e", "wpan.fcf",
    "-e", "wpan.seq_no",
    #"-e", "wpan.fcf_frame_type",
    #"-e", "wpan.fcf_ackreq",
    #"-e", "wpan.fcf_panidcompress",
    "-e", "wpan.dst_pan",
    "-e", "wpan.src64",
    "-e", "wpan.dst64",

    # 6LoWPAN
    "-e", "6lowpan.src",
    "-e", "6lowpan.dst",
    "-e", "6lowpan.iphc.tf",
    "-e", "6lowpan.iphc.nh",
    "-e", "6lowpan.iphc.hlim",
    "-e", "6lowpan.iphc.sam",
    "-e", "6lowpan.iphc.dam",

    "-E", "header=y",
    "-E", "separator=,",
    "-E", "quote=d"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:", result.stdout[:200])
    print("STDERR:", result.stderr)
    # comment in to avoid saving file
    with open("packets.csv", "w") as f:
        f.write(result.stdout)

    return result.stdout


def analyze(data_str, args: argparse.ArgumentParser):
    # Convert tshark output to pandas DataFrame
    df = pd.read_csv(StringIO(data_str))
    df = filter_frames(df, args.start, args.end)
    print(f"Analyzing {len(df)} frames...")
    # this part is random dummy code and should be replaced with actual analysis logic

    # df["time"] = pd.to_datetime(df["frame.time_epoch"], unit="s")

    # # Inter-arrival time
    # df["delta"] = df["frame.time_epoch"].diff()

    # # Throughput (kbps)
    df["time_bin"] = df["frame.time_epoch"].astype(int)
    throughput = df.groupby("time_bin")["frame.len"].sum() * 8 / 1000

    return df, throughput

def filter_frames(df, start=None, end=None):
    if start is not None:
        df = df[df["frame.number"] >= start]
    if end is not None:
        df = df[df["frame.number"] <= end]
    return df

def plot(throughput):
    throughput.plot(title="Throughput (kbps)")
    plt.xlabel("Time (s)")
    plt.ylabel("kbps")
    plt.grid()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PCAP Analyzer")

    parser.add_argument(
        "pcap",
        nargs="?",
        default="sniffa_file.pcap",
        help="Path to PCAP file"
    )

    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)

    args = parser.parse_args()

    raw_data = run_tshark(args.pcap) # run tshark to extract data from pcap file
    df, throughput = analyze(raw_data, args)  # analyze
    plot(throughput) # visualize

    print(df.head())