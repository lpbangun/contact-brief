"""Mock provider boundaries; never dispatch network from this suite."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class ExaTests(unittest.TestCase):
    def test_bounded_authorized_run_is_journaled_polled_and_not_duplicated(self):
        self.assertIsNotNone(importlib.util.find_spec('cb_providers'), 'provider helper missing')
        import cb_providers as p
        calls=[]
        def transport(method, path, payload, key):
            calls.append((method,path,payload))
            if method=='POST':return {'id':'agent_run_fixture','status':'queued'}
            return {'id':'agent_run_fixture','status':'completed','output':{'structured':{'name':'Fixture Person','email':'fixture@example.org'},'grounding':[{'url':'https://example.org/team'}]},'costDollars':{'total':0.04}}
        auth={'approved':True,'name':'Fixture Person','company':'Example Org','max_total_usd':0.05}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.json'
            result=p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            self.assertEqual(result['status'],'completed')
            self.assertNotIn('budget', calls[0][2])
            self.assertEqual(calls[0][2]['outputSchema']['properties']['email']['format'],'email')
            self.assertEqual(calls[0][2]['effort'],'low')
            self.assertNotIn('identity_notes', calls[0][2]['outputSchema']['properties'])
            self.assertIn('email only', calls[0][2]['query'])
            self.assertNotIn('fixture-key',path.read_text())
            self.assertEqual(result['output']['grounding'][0]['url'],'https://example.org/team')
            p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            self.assertEqual(sum(c[0]=='POST' for c in calls),1)
        for bad in ({**auth,'approved':False},{**auth,'max_total_usd':0.01},{**auth,'effort':'auto'},{**auth,'name':''}):
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):p.exa_run(bad,Path(tmp)/'j.json',key='fixture-key',transport=transport)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):p.exa_run(auth,Path(tmp)/'j.json',key='',transport=transport)

    def test_aftership_results_keep_dns_catchall_and_smtp_separate(self):
        import cb_providers as p
        self.assertTrue(callable(getattr(p,'aftership_result',None)), 'AfterShip normalization missing')
        raw={'email':'fixture@example.org','syntax':{'valid':True},'has_mx_records':True,'smtp':None}
        at='2026-09-08T12:00:00Z'
        self.assertEqual(p.aftership_result(raw,at,False)['status'],'unknown')
        raw['smtp']={'host_exists':True,'deliverable':True,'catch_all':False,'disabled':False,'full_inbox':False}
        self.assertEqual(p.aftership_result(raw,at,False)['status'],'unknown')
        self.assertEqual(p.aftership_result(raw,at,True)['status'],'smtp_accepted')
        self.assertIn('not a delivery guarantee',p.aftership_result(raw,at,True)['detail'])
        raw['smtp']['catch_all']=True
        self.assertEqual(p.aftership_result(raw,at,True)['status'],'risky')
        for error in ('timeout','blocked'):
            self.assertEqual(p.aftership_result(raw,at,True,error=error)['status'],'unknown')
        self.assertEqual(p.aftership_result({},at,True)['status'],'unknown')
        raw['syntax']['valid']=False
        self.assertEqual(p.aftership_result(raw,at,False)['status'],'invalid')

if __name__=='__main__':unittest.main()
