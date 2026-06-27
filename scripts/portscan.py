"""
A simple portscanner
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import socket

# Global configuration
COLORS = {
    "red": "\033[31m",
    "green": "\033[32m", 
    "blue": "\033[34m",
    "reset": "\033[0m",
}


# Helper functions
def perror(message: str) -> None:
    """Prints the error message and exits with exit-code 1."""
    print(message)
    exit(1)


# Logic
def scan(ip: str, port: int, timeout: float, banner_size: int, payload: str) -> dict | None:
    """Scans a port and returns a dict if open, or None if closed."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)

            if sock.connect_ex((ip, port)) == 0:
                try:
                    banner = sock.recv(banner_size).decode(errors="replace")
                except socket.timeout:
                    banner = ""

                if not banner:
                    try:
                        sock.sendall(payload.encode())
                        banner = sock.recv(banner_size).decode(errors="replace") or "open (no data)"
                    except socket.error:
                        banner = "open (no data)"

                return {"port": port, "banner": banner.strip()}

    except OSError as e:
        print(f"{COLORS['red']}E:{COLORS['reset']} {e}")
    
    return None


def parse_port_range(port_range: str) -> dict[str, int]:
    """Parses the given port-range string and returns start and end ports."""
    _range = {"start": 1, "end": 1024}
    
    one_to_n_pattern = r"^-\d+$"
    n_to_max_pattern = r"^\d+-$"
    standard_range_pattern = r"^\d+-\d+$"

    try:
        if re.match(n_to_max_pattern, port_range):
            _range["start"] = int(port_range.replace("-", ""))
            _range["end"] = 65535
        elif re.match(one_to_n_pattern, port_range):
            _range["start"] = 1       
            _range["end"] = int(port_range.replace("-", ""))
        elif re.match(standard_range_pattern, port_range):
            parts = port_range.split("-")
            _range["start"] = int(parts[0])
            _range["end"] = int(parts[1])
        else:
            raise ValueError("Format must be n-k, n-, or -n")

        return _range
 
    except ValueError as e:
        perror(f"{COLORS['red']}E: invalid range [debug-error: {e}]{COLORS['reset']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A simple portscanner")

    port_help_msg = (
        "specify the scan range:\n"
        "case 1: n-k. scans from n to k\n"
        "case 2: n-. scans from n to 65535\n"
        "case 3: -n. scans from 1 to n"
    )

    parser.add_argument("host", type=str, nargs="?", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=str, default="1-1024", help=port_help_msg)
    parser.add_argument("-t", "--timeout", type=float, default=1.0)
    parser.add_argument("--threads", type=int, default=200, help="number of threads to use. default is 200")
    parser.add_argument("--banner-size", type=int, default=4096, help="amount of data a banner holds. default is 4096 byte")
    parser.add_argument("--payload", type=str, default="", help="specify a payload to send (optional)")

    return parser.parse_args()


def main():
    args = parse_args()
    port_range = parse_port_range(args.port) 
    
    # Simple regex validation for IP or hostname format consistency
    if not re.match(r"^[a-zA-Z0-9.-]+$", args.host):
        perror(f"{COLORS['red']}E:{COLORS['reset']} '{args.host}' is not a valid target!")
    
    print(f"{COLORS['blue']}+ scanning{COLORS['reset']}: {args.host} ({args.timeout:.2f}s delay | range: {port_range["start"]}-{port_range["end"]})")
    print("-" * 75)

    with ThreadPoolExecutor(max_workers=args.threads) as t_exec:
        # FIXED: Created a proper dict comprehension mapping Future object -> Port Integer
        futures = {
            t_exec.submit(
                scan, args.host, port, args.timeout, args.banner_size, args.payload
            ): port 
            for port in range(port_range["start"], port_range["end"] + 1)
        }

        for future in as_completed(futures):
            port = futures[future]  # FIXED: Safely look up the port from the dictionary

            try:
                result = future.result()
                if result:
                    print(f"{COLORS['green']}{result['port']}{COLORS['reset']}: {result['banner']}")
            except Exception as e:
                print(f"{COLORS['red']}E:{COLORS['reset']} Port {port} raised {e}")


if __name__ == "__main__":
    main()