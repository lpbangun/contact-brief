import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class LiveHarnessTests(unittest.TestCase):
    def test_live_preflight_is_off_by_default_and_evidence_must_exist(self):
        self.assertTrue((ROOT/'scripts/live_test.py').is_file(),'opt-in harness missing')
        run=subprocess.run([sys.executable,str(ROOT/'scripts/live_test.py'),'preflight'],capture_output=True,text=True,env={**os.environ,'EXA_API_KEY':''})
        self.assertEqual(run.returncode,2)
        report=json.loads(run.stdout)
        self.assertFalse(report['passed'])
        self.assertIn('named contact and explicit approval',report['blockers'])
        self.assertIn('EXA_API_KEY missing',report['blockers'])
        import live_test
        import contact_brief as cb
        from test_gates import request
        with tempfile.TemporaryDirectory() as tmp:
            brief=cb.build(request())
            gate=live_test.verify_evidence(brief,Path(tmp),None)
            self.assertFalse(gate['passed'])
            self.assertTrue(any('evidence file' in b for b in gate['blockers']))
            self.assertTrue(any('Exa' in b for b in gate['blockers']))

    def test_supplied_complete_fixtures_never_attest_live_execution(self):
        import live_test
        import contact_brief as cb
        from test_gates import request, SOURCE
        data = request()
        data['candidate_facts'] = [{'id': 'f1', 'text': 'Fictional candidate fact', 'source': 'fixture'}]
        data['signals'] = [{**SOURCE, 'platform': 'x', 'authored': True,
                            'summary': 'Fictional post', 'relevance': 'Fixture only'}]
        brief = cb.build(data)
        journal = {'request': {'input': {'data': [brief['subject']]}},
                   'run': {'status': 'completed', 'output': {'grounding': [{'url': SOURCE['url']}]}}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'fixture-only.txt').write_text('Supplied fixture, NOT browser execution')
            report = live_test.verify_evidence(brief, tmp, journal)
        self.assertTrue(report['evidence_complete'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['live_execution'], 'not_verified')
        self.assertEqual(report['network_calls'], 0)

if __name__=='__main__':unittest.main()
