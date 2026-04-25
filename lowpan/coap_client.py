import asyncio
import aiocoap
import time
import argparse
import aiocoap.credentials
async def run_test(target, num_requests, payload_size, dtls = False, key = b'hejsa', identity = b'identity'):
    protocol = await aiocoap.Context.create_client_context()
    payload = b'A' * payload_size
    total_bytes = 0
    success = 0
    failed = 0
    if dtls:
        key = key.encode()
        identity = identity.encode()

        protocol.client_credentials.load_from_dict({
            target.rstrip('/') + '/*': {
                'dtls': {
                    'psk': key,
                    'client-identity': identity
                }
            }
        })
    print(f"Sending {num_requests} requests, payload size: {payload_size} bytes")
    print(f"Target: {target}")

    print("-" * 40)

    start = time.time()

    for i in range(num_requests):
        try:
            request = aiocoap.Message(
                code=aiocoap.GET,
                uri=target,
                payload=payload
            )
            response = await protocol.request(request).response
            if not response.code.is_successful():
                print(response.code)
            total_bytes += payload_size
            success += 1
        except Exception as e:
            print(f"Request {i+1} failed: {e}")
            failed += 1

    elapsed = time.time() - start
    throughput = (total_bytes * 8) / elapsed  # bits per second

    print(f"Requests: {num_requests}")
    print(f"Success: {success}")
    print(f"Failed: {failed}")
    print(f"Time: {elapsed:.2f} s")
    print(f"Throughput: {throughput:.2f} bps  ({throughput/1000:.2f} kbps)")
    print(f"Req/sec: {success/elapsed:.2f}")

    await protocol.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="coap://[ipv6addr%iface]")
    parser.add_argument("-n", type=int, default=100, help="number of requests")
    parser.add_argument("-s", type=int, default=64, help="payload size in bytes")
    parser.add_argument("--dtls", action="store_true", help="use DTLS with PSK")
    parser.add_argument("-key", type=str, default="hejsa", help="PSK key for DTLS")
    parser.add_argument("-u", type=str, default="identity", help="Client identity")
    args = parser.parse_args()

    asyncio.run(run_test(args.target, args.n, args.s, args.dtls, args.key, args.u))