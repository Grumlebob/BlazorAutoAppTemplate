"""Wait for exact application readiness; run full acceptance once afterwards."""
import sys
import time
import urllib.error
import urllib.request


READINESS_USER_AGENT = "BlazorAutoApp-Deployment-Readiness/1.0"


def build_request(url):
    return urllib.request.Request(url, headers={"User-Agent": READINESS_USER_AGENT})


def wait(url, timeout=180, label="LAN"):
    deadline = time.monotonic() + timeout
    last = "no response"
    attempts = 0
    print(f"Waiting up to {timeout} seconds for {label} readiness", flush=True)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError(f"{label} readiness deadline exceeded after {timeout} seconds ({last})")
        attempts += 1
        try:
            with urllib.request.urlopen(build_request(url), timeout=min(5, remaining)) as response:
                last = f"HTTP {response.status}"
                if response.status == 200 and response.read(64).strip() == b"Healthy":
                    print(f"{label} readiness returned 200 after {attempts} probes", flush=True)
                    return
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
            error.close()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = type(error).__name__
        time.sleep(min(2, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in ("LAN", "public")):
        raise SystemExit("Usage: readiness.py <health-ready-URL> [LAN|public]")
    try:
        # The label keeps a public probe failure from reading as a LAN problem.
        wait(sys.argv[1], label=sys.argv[2] if len(sys.argv) == 3 else "LAN")
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
