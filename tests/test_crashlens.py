import unittest
import tempfile
from pathlib import Path
from crashlens import analyze, redact, render_html, main

class LensTests(unittest.TestCase):
    def test_no_false_healthy(self):
        self.assertEqual(analyze(['INFO initialized'])['status'], 'insufficient_evidence')
    def test_oom_and_secondary_timeout(self):
        r=analyze(['2026-01-01T01:00:00Z CUDA out of memory\n2026-01-01T01:00:01Z NCCL timeout'])
        self.assertEqual([e['rule'] for e in r['events']], ['gpu_oom','nccl_timeout'])
    def test_timezone_sort(self):
        r=analyze(['2026-01-01T02:00:00+02:00 NCCL timeout','2026-01-01T00:30:00Z CUDA out of memory'])
        self.assertEqual(r['events'][0]['rule'],'nccl_timeout')
    def test_missing_time_keeps_input_order(self):
        r=analyze(['NCCL timeout','2026-01-01T00:00:00Z CUDA out of memory'])
        self.assertIn('unavailable',r['ordering'])
        self.assertEqual(r['events'][0]['rule'],'nccl_timeout')
    def test_redaction(self):
        self.assertNotIn('abc123',redact('token="abc123" Bearer abc123'))
        self.assertNotIn('test@example.com',redact('test@example.com'))
    def test_html_escape(self):
        h=render_html(analyze(['CUDA out of memory <script>alert(1)</script>']))
        self.assertNotIn('<script>',h)
        self.assertIn('&lt;script&gt;',h)
    def test_host_oom_is_distinct(self):
        self.assertEqual(analyze(['Out of memory: Killed process 22'])['counts'],{'host_oom':1})
    def test_duplicates_are_occurrences(self):
        self.assertEqual(analyze(['CUDA out of memory\nCUDA out of memory'])['counts']['gpu_oom'],2)
    def test_invalid_date(self):
        self.assertIsNone(analyze(['2026-99-99T10:00:00Z NCCL timeout'])['events'][0]['timestamp'])
    def test_cli_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input.log'; source.write_text('CUDA out of memory')
            out=Path(d)/'out'
            self.assertEqual(main([str(source),'--out',str(out)]),0)
            self.assertTrue((out/'report.html').exists())
            with self.assertRaises(SystemExit) as e: main([str(source),'--out',str(out)])
            self.assertEqual(e.exception.code,2)
    def test_binary_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'binary'; source.write_bytes(b'\x00')
            with self.assertRaises(SystemExit): main([str(source),'--out',d+'/out'])


class ClassificationTests(unittest.TestCase):
    def test_generic_nccl_warning_is_not_timeout(self):
        self.assertEqual(analyze(['NCCL WARN configuration fallback'])['events'], [])
    def test_gpu_lost_not_nvlink(self):
        self.assertEqual(analyze(['GPU is lost'])['counts'], {'gpu_lost':1})
    def test_slowdown_not_thermal(self):
        self.assertEqual(analyze(['HW Slowdown'])['counts'], {'hardware_slowdown':1})
    def test_explicit_thermal(self):
        self.assertEqual(analyze(['Thermal Throttling'])['counts'], {'thermal_message':1})
    def test_worker_pid(self):
        self.assertEqual(analyze(['Worker (pid:123) exited unexpectedly'])['counts'], {'worker_exit':1})
    def test_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input'; source.write_bytes(b'\xff')
            with self.assertRaises(SystemExit):
                main([str(source),'--out',d+'/out'])
            self.assertFalse((Path(d)/'out').exists())
    def test_size_limit(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'input'; source.write_text('CUDA out of memory')
            with patch('crashlens.MAX_BYTES', 4):
                with self.assertRaises(SystemExit):
                    main([str(source),'--out',d+'/out'])

if __name__=='__main__': unittest.main()
