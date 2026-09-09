"""Codex Exa plugin results are imported offline; no plugin or network calls occur here."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
AT = '2026-09-09T12:00:00Z'


def request():
    return {'name': 'Fixture Person', 'company': 'Example Org'}


def source():
    return {
        'url': 'https://example.org/team/fixture',
        'fetched_at': AT,
        'published_at': None,
        'quote': 'Fixture Person email is listed by Example Org.',
        'kind': 'exa',
    }


def plugin_result(address='fixture@example.org', *, name='Fixture Person', company='Example Org'):
    return {
        'route': 'codex_exa_plugin',
        'tool': 'exa_lookup_alias',
        'retrieved_at': AT,
        'status': 'completed' if address else 'no_result',
        'subject': {'name': name, 'company': company},
        'email': None if address is None else {
            'address': address,
            'sources': [source()],
        },
    }


def run_import(request_data, result_data):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        request_path = root / 'request.json'
        result_path = root / 'plugin-result.json'
        output_path = root / 'request-with-email.json'
        request_path.write_text(json.dumps(request_data))
        result_path.write_text(json.dumps(result_data))
        run = subprocess.run(
            [PYTHON, str(ROOT / 'scripts/contact_brief.py'), 'import-exa',
             str(request_path), '--result', str(result_path), '--out', str(output_path)],
            capture_output=True, text=True,
        )
        output = json.loads(output_path.read_text()) if output_path.exists() else None
        return run, output


class ExaPluginImportTests(unittest.TestCase):
    def test_imports_one_email_as_provider_reported_and_leaves_mailbox_unchecked(self):
        run, output = run_import(request(), plugin_result())
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(output['email']['address'], 'fixture@example.org')
        self.assertEqual(output['email']['attribution'], 'provider_reported')
        self.assertEqual(output['email']['evidence'][0]['url'], source()['url'])
        self.assertEqual(output['email']['mailbox']['status'], 'not_checked')
        self.assertEqual(output['email']['mailbox']['method'], 'none')
        self.assertIsNone(output['email']['mailbox']['checked_at'])

    def test_imports_no_result_without_requiring_an_api_key(self):
        run, output = run_import(request(), plugin_result(None))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(output['email']['address'], None)
        self.assertEqual(output['email']['attribution'], 'unknown')
        self.assertEqual(output['email']['mailbox']['status'], 'not_checked')

    def test_rejects_provider_result_for_a_different_subject(self):
        run, output = run_import(request(), plugin_result(name='Another Person'))
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(output)
        self.assertIn('Invalid evidence', run.stderr)

    def test_rejects_non_null_email_without_attribution_source(self):
        result = plugin_result()
        result['email']['sources'] = []
        run, output = run_import(request(), result)
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(output)
        self.assertIn('Invalid evidence', run.stderr)

    def test_rejects_multiple_addresses_in_provider_result(self):
        result = plugin_result()
        result['email']['address'] = ['one@example.org', 'two@example.org']
        run, output = run_import(request(), result)
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(output)

    def test_rejects_comma_separated_addresses_in_provider_result(self):
        result = plugin_result()
        result['email']['address'] = 'one@example.org, two@example.org'
        run, output = run_import(request(), result)
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(output)


if __name__ == '__main__':
    unittest.main()
