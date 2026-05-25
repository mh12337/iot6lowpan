import json
import argparse
import matplotlib.pyplot as plt

def plot_from_file(filename):
    with open(filename, "r") as f:
        data = json.load(f)

    rtt = data.get("rtt_ms", [])
    target = data.get("target", "unknown")

    x = list(range(len(rtt))) 

    plt.figure()
    plt.plot(x, rtt, marker='o')

    plt.xlabel("Packet (n)")
    plt.ylabel("Delay (ms)")
    plt.title(f"Ping Delay to {target}")

    for i, val in enumerate(rtt):
        plt.text(i, val, f"{val:.1f}", fontsize=8)

    plt.grid()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="JSON file with ping results")
    args = parser.parse_args()

    plot_from_file(args.file)