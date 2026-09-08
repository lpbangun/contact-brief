"""No external mailbox calls: subprocess boundary is mocked."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cb_providers as p

class AfterShipTests(unittest.TestCase):
    def test_requires_exact_address_approval_before_dispatch(self):
        self.assertTrue(callable(getattr(p, 'aftership_run', None)), 'executable wrapper missing')
        with patch('subprocess.run') as run:
            for auth in ({}, {'approved': True, 'address': 'other@example.invalid'}):
                with self.assertRaises(ValueError):
                    p.aftership_run('fixture@example.invalid', auth, adapter='/missing')
            run.assert_not_called()

    def test_dispatch_normalizes_and_fails_closed(self):
        auth = {'approved': True, 'address': 'fixture@example.invalid', 'smtp_approved': True}
        raw = {'email': auth['address'], 'syntax': {'valid': True}, 'smtp': {
            'host_exists': True, 'deliverable': True, 'catch_all': False,
            'full_inbox': False, 'disabled': False}}
        response = {'raw': raw, 'error': None, 'smtp_enabled': True}
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, json.dumps(response), '')) as run:
            result = p.aftership_run(auth['address'], auth, adapter='/adapter', smtp=True)
            self.assertEqual(result['mailbox']['status'], 'smtp_accepted')
            self.assertTrue(json.loads(run.call_args.kwargs['input'])['smtp'])
            self.assertEqual(result['raw'], raw)
        for failure in (subprocess.TimeoutExpired('/adapter', 1), FileNotFoundError()):
            with patch('subprocess.run', side_effect=failure):
                self.assertEqual(p.aftership_run(auth['address'], auth, adapter='/adapter')['mailbox']['status'], 'unknown')
        for bad in ('not JSON', json.dumps({'raw': raw, 'smtp_enabled': False}), '[]'):
            with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, bad, '')):
                self.assertEqual(p.aftership_run(auth['address'], auth, adapter='/adapter', smtp=True)['mailbox']['status'], 'unknown')
        with patch('subprocess.run') as run:
            with self.assertRaises(ValueError):
                p.aftership_run(auth['address'], {**auth, 'smtp_approved': False}, adapter='/adapter', smtp=True)
            run.assert_not_called()

    def test_cli_is_opt_in_and_real_adapter_invalid_syntax(self):
        root = Path(__file__).resolve().parents[1]
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            auth = Path(tmp) / 'auth.json'
            auth.write_text(json.dumps({'approved': True, 'address': 'not-an-address'}))
            cmd = [sys.executable, str(root / 'scripts/contact_brief.py'), 'verify-email', str(auth), '--adapter', str(root / 'bin/contact-brief-aftership')]
            blocked = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 2)
            if not (root / 'bin/contact-brief-aftership').exists():
                self.skipTest('optional Go adapter not built')
            result = subprocess.run(cmd + ['--execute'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['mailbox']['status'], 'invalid')
            self.assertFalse(report['smtp_enabled'])
            self.assertEqual(report['raw']['email'], 'not-an-address')

if __name__ == '__main__':
    unittest.main()
