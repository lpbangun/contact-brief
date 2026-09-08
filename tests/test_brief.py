"""All examples here are fictional deterministic fixtures, not research."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

class BriefTests(unittest.TestCase):
    def test_offline_brief_has_explicit_unknowns_and_two_platforms(self):
        self.assertIsNotNone(importlib.util.find_spec('contact_brief'), 'contact_brief implementation missing')
        import contact_brief as cb
        result = cb.build({'name': 'Fixture Person', 'company': 'Example Org'}, now='2026-09-08T12:00:00Z')
        self.assertEqual(result['schema_version'], 'contact-brief.v1')
        self.assertEqual(result['identity']['status'], 'unresolved')
        self.assertEqual(result['email']['mailbox']['status'], 'not_checked')
        self.assertEqual(set(result['coverage']), {'linkedin', 'x'})
        self.assertFalse(result['acceptance']['passed'])
        self.assertIn('not_attempted', cb.render(result))
        self.assertIsNone(result['draft'])

    def test_evidence_compiles_deduped_signals_with_dates_and_grounded_draft(self):
        import contact_brief as cb
        source = {'url': 'https://example.org/team/fixture', 'fetched_at': '2026-09-08T12:00:00Z',
                  'published_at': None, 'quote': 'Fixture Person leads Example Org', 'kind': 'company'}
        signal = {**source, 'url': 'https://x.com/fixture/status/123', 'platform': 'x',
                  'summary': 'Discussed professional mentoring', 'relevance': 'Networking purpose', 'authored': True}
        request = {'name': 'Fixture Person', 'company': 'Example Org',
                   'identity': {'status': 'matched', 'confidence': 'high', 'evidence': [source], 'conflicts': []},
                   'signals': [signal, signal],
                   'candidate_facts': [{'id': 'f1', 'text': 'I build learning tools.', 'source': 'user supplied'}]}
        result = cb.build(request)
        self.assertEqual(len(result['signals']), 1)
        self.assertIsNone(result['signals'][0]['published_at'])
        self.assertEqual(result['draft']['candidate_fact_ids'], ['f1'])
        self.assertIn('I build learning tools.', result['draft']['body'])
        self.assertIn('https://x.com/fixture/status/123', cb.render(result))
        self.assertIn('publication unknown', cb.render(result))
        self.assertTrue(callable(getattr(cb, 'validate', None)), 'schema validation missing')
        cb.validate(result)
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp)/'input.json'; inp.write_text(json.dumps(request))
            run = subprocess.run([sys.executable, str(ROOT/'scripts/contact_brief.py'), 'build',
                                  str(inp), '--out', str(Path(tmp)/'brief')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((Path(tmp)/'brief.json').read_text())['signals'], result['signals'])
            self.assertTrue((Path(tmp)/'brief.md').is_file())

    def test_cli_fixed_timestamp_is_reproducible_and_labels_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'input.json').write_text(json.dumps({'name': 'Fixture Person', 'company': 'Example Org'}))
            outputs = []
            for name in ('one', 'two'):
                run = subprocess.run([sys.executable, str(ROOT/'scripts/contact_brief.py'), 'build',
                                      str(root/'input.json'), '--out', str(root/name),
                                      '--now', '2026-09-08T12:00:00Z'], capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append((root/(name+'.json')).read_bytes())
            self.assertEqual(*outputs)
            self.assertIn('not live execution', (root/'one.md').read_text())

if __name__ == '__main__':
    unittest.main()
