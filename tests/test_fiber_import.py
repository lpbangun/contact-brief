"""Fiber Agent envelopes import offline with conservative contact semantics."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
AT = '2026-09-18T18:00:00Z'


def request():
    return {'name': 'Fixture Person', 'company': 'Example Org'}


def fiber_result(status='provider_reported', *, address='fixture@example.org', name='Fixture Person', company='Example Org'):
    return {
        'route': 'exa_agent_fiber',
        'tool': 'exa_agent_runs',
        'retrieved_at': AT,
        'status': status,
        'subject': {'name': name, 'company': company},
        'run_id': 'agent_run_fixture_123',
        'cost_usd': 0.045,
        'attribution': 'Fiber.ai contact_work_email result',
        'source_urls': [],
        'usage': {'agentComputeUnits': 0.1, 'searches': 3, 'emails': 1, 'phoneNumbers': 0},
        'cost': {'total': 0.045, 'agentCompute': 0.01, 'search': 0.015, 'emails': 0.02, 'phoneNumbers': 0,
                 'dataSources': {'fiber': 0.02}},
        'email': None if address is None else {'address': address},
    }


def run_import(request_data, result_data):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request_path = root / 'request.json'
        result_path = root / 'fiber-result.json'
        output_path = root / 'request-with-email.json'
        request_path.write_text(json.dumps(request_data))
        result_path.write_text(json.dumps(result_data))
        run = subprocess.run(
            [PYTHON, str(ROOT / 'scripts/contact_brief.py'), 'import-fiber',
             str(request_path), '--result', str(result_path), '--out', str(output_path)],
            capture_output=True, text=True,
        )
        output = json.loads(output_path.read_text()) if output_path.exists() else None
        return run, output


class FiberImportTests(unittest.TestCase):
    def test_accepts_provider_reported_email_without_source_url_and_preserves_metadata(self):
        run, output = run_import(request(), fiber_result())
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(output['email']['address'], 'fixture@example.org')
        self.assertEqual(output['email']['attribution'], 'provider_reported')
        self.assertEqual(output['email']['evidence'], [])
        self.assertEqual(output['email']['lookup']['status'], 'provider_reported')
        self.assertEqual(output['email']['lookup']['provider_run_id'], 'agent_run_fixture_123')
        self.assertEqual(output['email']['lookup']['cost_usd'], 0.045)
        self.assertEqual(output['email']['lookup']['usage']['emails'], 1)
        self.assertEqual(output['email']['lookup']['cost']['dataSources']['fiber'], 0.02)
        self.assertEqual(output['email']['mailbox']['status'], 'not_checked')

    def test_uncertain_provider_candidate_is_not_exposed_as_public_email(self):
        run, output = run_import(request(), fiber_result(status='uncertain'))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIsNone(output['email']['address'])
        self.assertEqual(output['email']['attribution'], 'unknown')
        self.assertEqual(output['email']['lookup']['status'], 'uncertain')
        self.assertEqual(output['email']['mailbox']['status'], 'not_checked')

    def test_not_found_result_is_a_valid_no_email_outcome(self):
        run, output = run_import(request(), fiber_result(status='not_found', address=None))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIsNone(output['email']['address'])
        self.assertEqual(output['email']['lookup']['status'], 'not_found')

    def test_rejects_subject_mismatch(self):
        run, output = run_import(request(), fiber_result(name='Another Person'))
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(output)
        self.assertIn('Invalid evidence', run.stderr)


if __name__ == '__main__':
    unittest.main()
