"""Provider boundary checks; no network calls."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

class ProviderTests(unittest.TestCase):
    def test_exa_fiber_lookup_removed(self):
        import cb_providers as p
        self.assertFalse(hasattr(p, "exa_run"))
        self.assertFalse(hasattr(p, "exa_http"))

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
