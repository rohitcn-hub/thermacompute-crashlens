import json
import tempfile
import unittest
from pathlib import Path
from crashlens import analyze, main, render_html, markdown

class InvestigationTests(unittest.TestCase):
    def pair(self, delta='00:01:00', other='train'):
        return ["2026-10-08T00:00:00Z job=train rank=0 gpu=GPU-a CUDA out of memory",f"2026-10-08T{delta}Z job={other} rank=1 NCCL timeout"]
    def test_peer_failure_is_candidate_not_cause(self):
        r=analyze(self.pair());self.assertEqual(len(r['relationships']),1)
        self.assertEqual(r['relationships'][0]['observed_delta_seconds'],60)
        self.assertIn('not stall duration',r['relationships'][0]['limitation'])
        self.assertEqual(r['events'][0]['identity']['gpu'],'GPU-a')
    def test_separate_jobs_never_join(self):
        self.assertEqual(analyze(self.pair(other='other'))['relationships'],[])
    def test_missing_identity_never_join(self):
        self.assertEqual(analyze([x.replace('job=train ','') for x in self.pair()])['relationships'],[])
    def test_same_rank_is_not_cross_rank(self):
        self.assertEqual(analyze([x.replace('rank=1','rank=0') for x in self.pair()])['relationships'],[])
    def test_window_and_ties(self):
        for stamp in ['00:02:01','00:00:00']:
            self.assertEqual(analyze(self.pair(delta=stamp))['relationships'],[])
    def test_nearest_preceding_failure(self):
        r=analyze(self.pair()+['2026-10-08T00:00:30Z job=train rank=2 Worker failed with error'])
        ids={e['id']:e for e in r['events']};self.assertEqual(ids[r['relationships'][0]['from']]['identity']['rank'],'2')
    def test_fractional_timestamps_sort_numerically(self):
        r=analyze(['2026-10-08T00:00:00.1Z NCCL timeout','2026-10-08T00:00:00Z CUDA out of memory'])
        self.assertEqual(r['events'][0]['rule'],'gpu_oom')
    def test_conflicting_identity_not_chosen(self):
        r=analyze(['job=a job=b rank=0 CUDA out of memory'])
        self.assertNotIn('job',r['events'][0]['identity'])
    def test_context_redacted_and_html_escaped(self):
        r=analyze(['token=secret-value\nCUDA out of memory <img src=x onerror=alert(1)>\npassword=hidden'])
        h=render_html(r);self.assertNotIn('secret-value',h);self.assertNotIn('password=hidden',h)
        self.assertNotIn('<img',h);self.assertIn('&lt;img',h)
        self.assertIn('id="E0001"',h);self.assertIn('href="#E0001"',h)
    def test_no_match_is_inconclusive(self):
        r=analyze(['INFO fine']);self.assertIn('Insufficient evidence',r['summary']);self.assertEqual(r['priorities'],[])
    def test_folder_cli_report_and_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);logs=root/'logs';logs.mkdir()
            for i,text in enumerate(self.pair()):(logs/f'{i}.log').write_text(text)
            (logs/'ignore.csv').write_text('ignored')
            out=root/'report';self.assertEqual(main([str(logs),'--out',str(out)]),0)
            r=json.loads((out/'report.json').read_text());self.assertEqual(r['input_count'],2)
            self.assertEqual(len(r['sources'][0]['sha256']),64)
            self.assertIn('Cross-rank candidates',(out/'report.md').read_text())
            self.assertNotIn(str(logs),(out/'report.html').read_text())
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.log';p.write_text('NCCL timeout')
            with self.assertRaises(SystemExit):main([str(p),str(p),'--out',tmp+'/out'])
    def test_match_flood_rejected(self):
        with self.assertRaisesRegex(ValueError,'5000'):analyze(['NCCL timeout\n'*5001])
    def test_missing_time_not_correlated(self):
        self.assertEqual(analyze(['job=train rank=0 CUDA out of memory',self.pair()[1]])['relationships'],[])

if __name__=='__main__':unittest.main()
