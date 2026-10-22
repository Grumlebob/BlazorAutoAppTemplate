"""Keep the shared Docker daemon's BuildKit cache under a byte budget.

Only build cache is trimmed, least recently used first. BuildKit can rebuild every entry, so the
trim never touches images, containers, volumes or networks that apps on this node depend on.
Cache records in use by a running build are kept by BuildKit itself.
"""
import argparse
import json
import re
import subprocess
import sys

DEFAULT_KEEP_GB = 20
MIN_KEEP_GB = 5
MAX_KEEP_GB = 500
_UNITS = {"B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4}


def run(*args, timeout=60):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError(f"{' '.join(args[:3])} failed (exit {result.returncode}): {result.stderr.strip()[:300]}")
    return result.stdout


def parse_size(text):
    """Parse Docker's human sizes such as 82GB, 48.85GB, 110.6kB or 0B into bytes."""
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([kKMGT]?B)\s*", text or "")
    if not match:
        raise ValueError(f"unrecognised Docker size: {text!r}")
    return round(float(match.group(1)) * _UNITS[match.group(2).upper()])


def build_cache_bytes(system_df_output):
    """Return (size, reclaimable) in bytes for the Build Cache row of `docker system df --format json`."""
    for line in system_df_output.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("Type") == "Build Cache":
            reclaimable = (row.get("Reclaimable") or "0B").split(" ")[0]
            return parse_size(row.get("Size") or "0B"), parse_size(reclaimable)
    return 0, 0


def keep_flag(prune_help):
    """Pick the flag that caps the cache at the budget on this Docker client.

    Docker 28 split --keep-storage into --max-used-space (the cap) and --reserved-space (a floor
    that is always kept); Docker 29 no longer offers --keep-storage.
    """
    for flag in ("--max-used-space", "--reserved-space"):
        if flag in prune_help:
            return flag
    return "--keep-storage"


def prune_command(keep_gb, flag):
    return ["docker", "builder", "prune", "--force", flag, f"{keep_gb}GB"]


def gigabytes(value):
    return f"{value / 1000 ** 3:.2f} GB"


def measure(runner):
    return build_cache_bytes(runner("docker", "system", "df", "--format", "{{json .}}", timeout=300))


def main(argv=None, runner=run):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep-gb", type=int, default=DEFAULT_KEEP_GB,
                        help=f"BuildKit cache budget in GB to keep (default {DEFAULT_KEEP_GB})")
    parser.add_argument("--dry-run", action="store_true", help="Report the cache and the planned trim only")
    args = parser.parse_args(argv)
    if not MIN_KEEP_GB <= args.keep_gb <= MAX_KEEP_GB:
        raise ValueError(f"--keep-gb must be between {MIN_KEEP_GB} and {MAX_KEEP_GB}")

    size, reclaimable = measure(runner)
    print(f"BuildKit cache before: {gigabytes(size)} ({gigabytes(reclaimable)} reclaimable); budget {args.keep_gb} GB")
    command = prune_command(args.keep_gb, keep_flag(runner("docker", "builder", "prune", "--help")))
    if args.dry_run:
        print("Dry run; would run: " + " ".join(command))
        return 0
    if size <= args.keep_gb * 1000 ** 3:
        print("BuildKit cache is within its budget; nothing to trim.")
        return 0
    runner(*command, timeout=1800)
    after, _ = measure(runner)
    print(f"BuildKit cache after: {gigabytes(after)}; trimmed {gigabytes(max(size - after, 0))}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
