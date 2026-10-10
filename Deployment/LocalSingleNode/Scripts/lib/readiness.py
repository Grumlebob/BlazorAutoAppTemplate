"""Wait only for LAN readiness; run the full acceptance check once afterwards."""
import sys
import time
import urllib.error
import urllib.request


def wait(url, timeout=180):
    deadline = time.monotonic() + timeout
    last = "no response"
    attempts = 0
    print(f"Waiting up to {timeout} seconds for LAN readiness", flush=True)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError(f"LAN readiness deadline exceeded after {timeout} seconds ({last})")
        attempts += 1
        try:
            with urllib.request.urlopen(url, timeout=min(5, remaining)) as response:
                last = f"HTTP {response.status}"
                if response.status == 200:
                    print(f"LAN readiness returned 200 after {attempts} probes", flush=True)
                    return
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
            error.close()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = type(error).__name__
        time.sleep(min(2, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: readiness.py <LAN-health-ready-URL>")
    try:
        wait(sys.argv[1])
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
