import sys
from copy import deepcopy
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import contact_brief as cb

AT = '2026-09-08T12:00:00Z'
SOURCE = {'url':'https://example.org/team', 'kind':'company', 'quote':'Fixture Person works at Example Org', 'published_at':None, 'fetched_at':AT}

def native(platform):
    base = 'https://www.linkedin.com' if platform == 'linkedin' else 'https://x.com'
    return {'status':'complete','reason':'Fixture native workflow', 'profile_url':base+'/fixture', 'identity_matched':True,
            'actions':[{'kind':k,'query':'Fixture Person' if 'search' in k else None,'url':base+'/search',
                        'fetched_at':AT,'outcome':'ok','evidence_file':'fixture-only.txt'}
                       for k in ('person_search','profile_open','activity_search','activity_inspect')]}

def request():
    return {'name':'Fixture Person', 'company':'Example Org',
            'identity':{'status':'matched','confidence':'high','evidence':[SOURCE], 'conflicts':[]},
            'coverage':{p:native(p) for p in ('linkedin','x')}}

class EvidenceGateTests(unittest.TestCase):
    def test_both_native_workflows_required_and_fallback_cannot_pass(self):
        data=request()
        self.assertTrue(cb.build(data)['acceptance']['passed'])
        for p in ('linkedin','x'):
            for kind in ('person_search','profile_open','activity_search','activity_inspect'):
                bad=deepcopy(data)
                bad['coverage'][p]['actions']=[a for a in bad['coverage'][p]['actions'] if a['kind'] != kind]
                self.assertFalse(cb.build(bad)['acceptance']['passed'], (p,kind))
            bad=deepcopy(data)
            bad['coverage'][p]['actions'][0]['url']='https://exa.ai/search'
            self.assertFalse(cb.build(bad)['acceptance']['passed'])
        for status in ('ambiguous','stale_employer','unresolved'):
            bad=deepcopy(data); bad['identity']['status']=status
            self.assertFalse(cb.build(bad)['acceptance']['passed'])
        for status in ('no_results','inactive','blocked','partial','not_attempted'):
            bad=deepcopy(data); bad['coverage']['linkedin']['status']=status
            self.assertFalse(cb.build(bad)['acceptance']['passed'])

    def test_unsupported_identity_and_mailbox_claims_are_rejected(self):
        bad=cb.build({'name':'Fixture Person','company':'Example Org'})
        bad['identity'].update(status='matched', confidence='high')
        with self.assertRaises(ValueError): cb.validate(bad)
        bad=cb.build({'name':'Fixture Person','company':'Example Org'})
        bad['email']['mailbox'].update(status='smtp_accepted', method='aftership_dns', checked_at=AT)
        with self.assertRaises(ValueError): cb.validate(bad)
        bad=cb.build({'name':'Fixture Person','company':'Example Org'})
        bad['email'].update(address='fixture@example.org',attribution='source_supported')
        with self.assertRaises(ValueError): cb.validate(bad)
        bad=cb.build({'name':'Fixture Person','company':'Example Org'})
        bad['acceptance']['passed']=True
        with self.assertRaises(ValueError): cb.validate(bad)

if __name__=='__main__': unittest.main()
