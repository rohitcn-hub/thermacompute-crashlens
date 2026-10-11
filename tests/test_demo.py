import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from demo import main


class DemoTests(unittest.TestCase):
    def test_scenarios_generate_labeled_reports(self):
        for scenario, count, status in [('oom', 3, 'matches_found'), ('thermal', 2, 'matches_found'), ('unknown', 0, 'insufficient_evidence')]:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'report'
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['--scenario', scenario, '--out', str(out)]), 0)
                report = json.loads((out / 'report.json').read_text())
                self.assertEqual(len(report['events']), count)
                self.assertEqual(report['status'], status)
                self.assertTrue(report['demo']['synthetic'])
                self.assertIn('SYNTHETIC DEMO ONLY', (out / 'report.html').read_text())
                self.assertIn('SYNTHETIC DEMO ONLY', (out / 'report.md').read_text())
                self.assertIn((out / 'report.html').as_uri(), output.getvalue())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'existing'
            out.mkdir()
            marker = out / 'report.json'
            marker.write_text('keep me')
            with self.assertRaises(SystemExit):
                main(['--out', str(out)])
            self.assertEqual(marker.read_text(), 'keep me')

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(SystemExit):
            main(['--scenario', 'production'])


if __name__ == '__main__':
    unittest.main()
