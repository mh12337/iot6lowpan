import subprocess
import time
import argparse

def run_test(target, num_requests, payload_size, dtls=False, key=None, identity=None):
    payload = 'A' * payload_size
    total_bytes = 0
    success = 0
    failed = 0

    cmd = ['coap-client', '-m', 'get', target, '-e', payload]
    cmd += ['-u', identity]
    if dtls:
        cmd += ['-k', key]
    print(f"Sending {num_requests} requests, payload size: {payload_size} bytes")
    print(f"Target: {target}")
    print(f"DTLS: {dtls}")
    print("-" * 40)

    start = time.time()

    for i in range(num_requests):
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                success += 1
                total_bytes += payload_size
            else:
                failed += 1
        except subprocess.TimeoutExpired:
            failed += 1

    elapsed = time.time() - start
    throughput = (total_bytes * 8) / elapsed

    print(f"Requests:   {num_requests}")
    print(f"Success:    {success}")
    print(f"Failed:     {failed}")
    print(f"Time:       {elapsed:.2f} s")
    print(f"Throughput: {throughput:.2f} bps ({throughput/1000:.2f} kbps)")
    print(f"Req/sec:    {success/elapsed:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="coap:// or coaps:// URI")
    parser.add_argument("-n", type=int, default=50, help="number of requests")
    parser.add_argument("-s", type=int, default=64, help="payload size in bytes")
    parser.add_argument("--dtls", action="store_true", help="enable DTLS")
    parser.add_argument("-k", default="h", help="DTLS key")
    parser.add_argument("-u", default="identity", help="DTLS identity")
    args = parser.parse_args()

    run_test(args.target, args.n, args.s, args.dtls, args.k, args.u)