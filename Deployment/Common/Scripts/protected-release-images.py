#!/usr/bin/env python3
"""Print immutable image protection from an existing locked status snapshot."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "Component/lib"))
import pin_release_payload
from release_status import ReleaseStatusError, protected_application_image_references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-json", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--app-image", required=True)
    args = parser.parse_args()
    try:
        pin_release_payload._require_shared_lock()
        path = args.status_json
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
            raise ReleaseStatusError("image protection status file is unsafe or exceeds its bound")
        status = json.loads(path.read_text(encoding="utf-8"))
        for reference in protected_application_image_references(
                status, repository=args.repository, app_image=args.app_image):
            print(reference)
    except (OSError, ValueError, ReleaseStatusError) as error:
        print("Image cleanup deferred; protected release state is unavailable: " + str(error), file=sys.stderr)
        return 75
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
