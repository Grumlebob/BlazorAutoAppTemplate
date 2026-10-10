"""Read a reviewed Linux x64 release version or published archive checksum."""
import json
from pathlib import Path
import re
import sys

values = json.loads((Path(__file__).resolve().parents[1] / "tool-versions.json").read_text())
if len(sys.argv) != 3 or sys.argv[1] not in values or sys.argv[2] not in ("version", "sha256"):
    raise SystemExit("Usage: read-tool-version.py <runner|gh> <version|sha256>")
tool = values[sys.argv[1]]
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", tool["version"]) or not re.fullmatch(r"[0-9a-f]{64}", tool["sha256"]):
    raise SystemExit("Invalid reviewed tool pin")
print(tool[sys.argv[2]])
