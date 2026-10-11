"""The runner handoff copies public code and cleans its own temporary directory."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "authorize-controller-ssh.sh"


@unittest.skipIf(os.name == "nt", "Runner wrapper requires native Linux shell tools")
class ControllerSshRunnerTests(unittest.TestCase):
    def fixture(self, fail):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "bin"
            binary.mkdir()
            python = binary / "python3"
            python.write_text('#!/bin/sh\ncase "$1" in\n */platform_check.py) exit 0 ;;\n -) cat >/dev/null; printf "operator\\n"; exit 0 ;;\nesac\nexec "$REAL_PYTHON" "$@"\n')
            sudo = binary / "sudo"
            sudo.write_text('''#!/bin/sh
set -eu
test "$1" = -n && test "$2" = -u && test "$3" = operator
test "$4" = -H && test "$5" = -- && test "$6" = python3
test "$8" = authorize && test "$9" = --repo
test "${10}" = example/app && test "${11}" = --controller && test "${12}" = main-pc
printf '%s' "$7" > "$HANDOFF_RECORD"
# Import the copied program and shared modules without running native authorization.
"$REAL_PYTHON" "$7" --help >/dev/null
exit "$FIXTURE_EXIT"
''')
            python.chmod(0o755)
            sudo.chmod(0o755)
            record = root / "record"
            environment = {**os.environ, "PATH": str(binary) + ":" + os.environ["PATH"],
                           "REAL_PYTHON": sys.executable, "HANDOFF_RECORD": str(record),
                           "FIXTURE_EXIT": "7" if fail else "0"}
            result = subprocess.run(["bash", str(SCRIPT), "example/app", "main-pc"],
                                    capture_output=True, text=True, env=environment)
            self.assertEqual(7 if fail else 0, result.returncode, result.stderr)
            copied_script = Path(record.read_text())
            self.assertFalse(copied_script.exists())
            self.assertNotIn("operator", result.stdout)
            self.assertEqual("", result.stderr)

    def test_success_uses_original_user_and_removes_temporary_program(self):
        self.fixture(False)

    def test_failure_propagates_and_removes_temporary_program(self):
        self.fixture(True)


if __name__ == "__main__":
    unittest.main()
