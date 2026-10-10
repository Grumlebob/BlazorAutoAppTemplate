"""Offline readiness deadlines and exactly-once full acceptance contracts."""
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

LIB = Path(__file__).resolve().parents[1] / 'lib'
sys.path.insert(0, str(LIB))
import readiness


class ReadinessTests(unittest.TestCase):
    def clock(self):
        clock = SimpleNamespace(value=0)
        def sleep(seconds):
            clock.value += seconds
        return clock, sleep

    def test_warmup_retries_only_health_then_returns(self):
        clock, sleep = self.clock()
        response = MagicMock()
        response.__enter__.return_value.status = 200
        attempts = [urllib.error.HTTPError('http://192.0.2.10/health/ready', 503, 'starting', {}, None), urllib.error.URLError('connection refused'), response]
        with patch.object(readiness.time, 'monotonic', side_effect=lambda: clock.value), patch.object(readiness.time, 'sleep', side_effect=sleep), patch.object(readiness.urllib.request, 'urlopen', side_effect=attempts) as request, patch('sys.stdout', new_callable=io.StringIO) as output:
            readiness.wait('http://192.0.2.10/health/ready')
            self.assertEqual(3, request.call_count)
            self.assertTrue(all(call.args == ('http://192.0.2.10/health/ready',) and call.kwargs['timeout'] == 5 for call in request.call_args_list))
            self.assertEqual(4, clock.value)
            self.assertIn('returned 200 after 3 probes', output.getvalue())

    def test_unhealthy_service_fails_at_the_deadline(self):
        clock, sleep = self.clock()
        with patch.object(readiness.time, 'monotonic', side_effect=lambda: clock.value), patch.object(readiness.time, 'sleep', side_effect=sleep), patch.object(readiness.urllib.request, 'urlopen', side_effect=urllib.error.URLError('not ready')) as request, patch('sys.stdout', new_callable=io.StringIO), self.assertRaisesRegex(ValueError, 'deadline exceeded after 4 seconds'):
            readiness.wait('http://192.0.2.10/health/ready', timeout=4)
        self.assertEqual(4, clock.value)
        self.assertEqual(2, request.call_count)

    def test_full_acceptance_runs_once_after_successful_warmup(self):
        text = (LIB.parent / 'acceptance-check.sh').read_text()
        self.assertLess(text.index('lib/readiness.py'), text.index('exec pwsh'))
        self.assertEqual(1, text.count('Scripts/Test-DeployedSite.ps1'))
        self.assertIn('set -euo pipefail', text)


if __name__ == '__main__':
    unittest.main()
