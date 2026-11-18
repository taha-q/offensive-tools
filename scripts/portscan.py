#!/usr/bin/env python3
"""
A simple async portscanner
"""

import argparse
import asyncio
import logging
import sys
import time

# Fixed logging format: changed 'level' to 'levelname'
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s | %(message)s",
    level=logging.WARNING,
    datefmt="%H:%M:%S"
)

def parse_port_range(port_str: str) -> tuple[int, ...]:
    """ 
    parses the following cases:
        case 1: n-k -> scans from n to k
        case 2: n-  -> scans from n to 65535
        case 3: -n  -> scans from 1 to n
        case 4: x,y,z (or mixed like 80,443,1000-2000)
    """
    port_str = port_str.strip()
    ports = set()

    # Case 4: Comma separated values
    if "," in port_str:
        for part in port_str.split(","):
            if part.strip():
                ports.update(parse_port_range(part))
        return tuple(sorted(ports))

    # Single port case
    if "-" not in port_str:
        try:
            p = int(port_str)
            return (p,)
        except ValueError as e:
            logging.error(f"Invalid port '{port_str}': {e}")
            return ()

    # Cases 1, 2, and 3 (hyphen ranges)
    start_str, _, end_str = port_str.partition("-")
    
    start = int(start_str) if start_str else 1
    end = int(end_str) if end_str else 65535
    
    return tuple(range(start, end + 1))


async def is_open(host: str, port: int, timeout: float, semaphore: asyncio.Semaphore) -> tuple[int, bool]:
    """ checks a single port if open with concurrency throttling """
    async with semaphore:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            logging.debug(f"Port {port} is open")
            return port, True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            logging.debug(f"Port {port} is closed/filtered")
            return port, False


async def main_async():
    parser = argparse.ArgumentParser(description="A clean, blazing-fast async port scanner.")
    parser.add_argument("host", help="Target IP address or hostname")
    parser.add_argument("-p", "--ports", default="1-1024", help="Port range (e.g. 80, 1-1000, -80, 443-, 80,443)")
    parser.add_argument("-t", "--timeout", type=float, default=1.0, help="Connection timeout in seconds")
    parser.add_argument("-c", "--concurrency", type=int, default=500, help="Max concurrent connections")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v for info, -vv or -vvv for debug)")

    args = parser.parse_args()

    # Configure logging levels based on -v flags
    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    ports = parse_port_range(args.ports)
    if not ports:
        logging.error("No valid ports parsed. Exiting.")
        sys.exit(1)

    logging.info(f"Target: {args.host} | Scanning {len(ports)} ports | Concurrency: {args.concurrency}")
    
    semaphore = asyncio.Semaphore(args.concurrency)
    start_time = time.time()

    # Fire off all checks concurrently with throttling
    tasks = [is_open(args.host, port, args.timeout, semaphore) for port in ports]
    results = await asyncio.gather(*tasks)

    open_ports = [port for port, status in results if status]
    elapsed = time.time() - start_time

    print(f"\n--- Scan Results for {args.host} ---")
    if open_ports:
        for p in sorted(open_ports):
            print(f"[+] Port {p}/tcp OPEN")
    else:
        print("[-] No open ports found.")
    print(f"[*] Completed in {elapsed:.2f}s")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Scan aborted by user. Exiting")
        sys.exit(0)


if __name__ == "__main__":
    main()