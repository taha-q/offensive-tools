#!/usr/bin/env python3

"""
a basic directory bruteforcer
"""

import argparse, asyncio, logging, sys
import string, random
try: import aiohttp
except ImportError: sys.exit("[!] Missing aiohttp: pip install aiohttp")

VALID = {200, 204, 301, 302, 307, 403}
G, Y, B, R, X = '\033[92m', '\033[93m', '\033[94m', '\033[91m', '\033[0m'

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)

async def detect_wildcard(url: str, session, check_count: int) -> bool:
    hits: int = 0
    count = 20 if not check_count else check_count
    min_required_hits = count // 2
    timeout = 3.0

    print(f"{B}[*]{X} Running wildcard checks ({count} requests)...")
    for _ in range(count):
        logging.info("running wildcard check iteration")
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        target   = f"{url.rstrip('/')}/{rand_str}"

        try:
            async with session.get(target, timeout=timeout) as s:
                if s.status in VALID:
                    hits += 1
        except Exception as e:
            logging.error(str(e))

    if hits > min_required_hits:
        logging.warning(f"Target could be a wildcard! HITS: {hits}/{count}. MIN REQUIRED: {min_required_hits}")
        print(f"{Y}[!]{X} Wildcard detected! Hits: {hits}/{count}")
        return True
    
    print(f"{G}[+]{X} No wildcard behavior detected.")
    return False

async def check(url, path, session, sem, timeout):
    target = f"{url.rstrip('/')}/{path.lstrip('/')}"
    async with sem:
        try:
            async with session.get(target, timeout=timeout) as r:
                if r.status in VALID:
                    color = G if r.status == 200 else Y
                    print(f"{color}[{r.status}]{X} {target}")
                    logging.info(f"Found: [{r.status}] {target}")
        except Exception as e:
            logging.debug(f"Failed {target}: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("-w", "--wordlist", required=True)
    parser.add_argument("-t", "--timeout", type=float, default=1.0)
    parser.add_argument("-c", "--concurrency", type=int, default=100)
    parser.add_argument("-o", "--output", help="Save discovered paths to a log file")
    parser.add_argument("--detect-wildcard", action="store_true", help="try to detect wildcards")
    parser.add_argument("--checks", type=int, default=20, help="how many times a check should run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.output:
        fh = logging.FileHandler(args.output)
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s"))
        logging.getLogger().addHandler(fh)

    with open(args.wordlist) as f:
        words = [l.strip() for l in f if l.strip()]
    
    logging.info(f"Loaded {len(words)} words from {args.wordlist}")
    print(f"{B}[*]{X} Scanning target: {args.url}")
    
    sem = asyncio.Semaphore(args.concurrency)
    async with aiohttp.ClientSession() as session:
        if args.detect_wildcard:
            if await detect_wildcard(args.url, session, args.checks):
                input("proceed [ENTER=Yes/CRTL+C=No]")
        await asyncio.gather(*(check(args.url, w, session, sem, args.timeout) for w in words))
    
    logging.info("Scan completed.")
    print(f"\n{B}[*]{X} Done")

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: sys.exit("\n[!] Aborted")