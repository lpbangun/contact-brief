"""Mock provider boundaries; never dispatch network from this suite."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

FIXTURE_QUERY=('Find a professional email only for this already identified person at the supplied company. '
               'Return at most one professional email, only if attributable; do not guess. '
               'Cite email attribution sources. Return null if uncertain. No social discovery, activity research, '
               'dossiers, phone numbers, mailbox verification or unrelated enrichment.')


def expected_request(auth):
    """The frozen direct Agent API request contract for one person, email only."""
    return {
        'query': FIXTURE_QUERY,
        'input': {'data': [{'name': auth['name'], 'company': auth['company']}]},
        'dataSources': [{'provider': 'fiber'}],
        'effort': 'low',
        'outputSchema': {'type': 'object', 'properties': {
            'email': {'type': 'string', 'format': 'email'},
            'email_attribution': {'type': 'string'},
            'source_urls': {'type': 'array', 'maxItems': 5, 'items': {'type': 'string', 'format': 'uri'}}}}}

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

    def test_post_payload_is_exactly_one_person_one_email_with_the_fiber_datasource(self):
        import cb_providers as p
        calls=[]
        def transport(method, path, payload, key):
            calls.append((method,path,payload))
            return {'id':'agent_run_fixture','status':'queued'} if method=='POST' else {'id':'agent_run_fixture','status':'completed'}
        auth={'approved':True,'name':'Fixture Person','company':'Example Org','max_total_usd':0.045}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.json'
            p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            sent=calls[0][2]
            self.assertEqual(calls[0][:2],('POST','/agent/runs'))
            # Exact request shape: any drift in the frozen contract fails here.
            self.assertEqual(sent,expected_request(auth))
            self.assertEqual(sorted(sent),['dataSources','effort','input','outputSchema','query'])
            self.assertEqual(sent['dataSources'],[{'provider':'fiber'}])
            self.assertEqual(sent['effort'],'low')
            self.assertEqual(sent['input'],{'data':[{'name':'Fixture Person','company':'Example Org'}]})
            self.assertEqual(len(sent['input']['data']),1)
            self.assertEqual(sorted(sent['outputSchema']['properties']),['email','email_attribution','source_urls'])
            for forbidden in ('phones','personal_email','dossier','activity','bulk','people'):
                self.assertNotIn(forbidden,sent)
            # The journal fingerprints the same request, including the datasource.
            self.assertEqual(json.loads(path.read_text())['request'],expected_request(auth))

    def test_replay_resumes_the_journal_instead_of_posting_a_second_time(self):
        import cb_providers as p
        calls=[]
        def transport(method, path, payload, key):
            calls.append((method,path,payload))
            if method=='POST':return {'id':'agent_run_fixture','status':'queued'}
            return {'id':'agent_run_fixture','status':'completed','costDollars':{'total':0.025}}
        auth={'approved':True,'name':'Fixture Person','company':'Example Org','max_total_usd':0.05}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.json'
            first=p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            self.assertEqual([c[0] for c in calls],['POST','GET'])
            second=p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            self.assertEqual([c[0] for c in calls],['POST','GET'],'a replay must resume, not dispatch again')
            self.assertEqual(first,second)
            self.assertEqual(json.loads(path.read_text())['dispatch'],'created')

    def test_journal_without_the_fiber_datasource_is_refused_without_any_post(self):
        import cb_providers as p
        calls=[]
        def transport(method, path, payload, key):
            calls.append((method,path,payload))
            return {'id':'agent_run_fixture','status':'queued'}
        auth={'approved':True,'name':'Fixture Person','company':'Example Org','max_total_usd':0.05}
        legacy=expected_request(auth)
        del legacy['dataSources']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.json'
            path.write_text(json.dumps({'request':legacy,'dispatch':'uncertain','fetched_at':None}))
            with self.assertRaises(ValueError):p.exa_run(auth,path,key='fixture-key',transport=transport,polls=1,interval=0)
            self.assertEqual(calls,[],'a mismatched journal must never reach the transport')
            self.assertEqual(json.loads(path.read_text())['request'],legacy,'the refused journal is left untouched')

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
