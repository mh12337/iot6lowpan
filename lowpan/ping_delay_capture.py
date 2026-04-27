import subprocess
from datetime import datetime
import json
import argparse
import re

def run_test(target, count):
    result = subprocess.run(['ping6', '-c', str(count), str(target)], capture_output=True, text=True)
    times = re.findall(r'time=([\d.]+)', result.stdout)
    data = {
        "target": target,
        "rtt_ms": [float(t) for t in times]
    }
    timestamp = datetime.now().strftime("%H%M%S")
    with open(f"ping_results_{target}_{timestamp}.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved ping results to ping_results_{target}_{timestamp}.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="ipv6 address of target")
    parser.add_argument("-n", type=int, default=10, help="number of ping requests")
    args = parser.parse_args()

    run_test(args.target, args.n)