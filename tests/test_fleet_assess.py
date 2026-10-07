import tempfile
import unittest
from pathlib import Path
from fleet_assess import assess

HEADER = 'timestamp,gpu_id,temperature_c,power_w,thermal_throttle\n'


class FleetTests(unittest.TestCase):
    def run_data(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.csv'
            path.write_text(text, encoding='utf-8')
            return assess(path)

    def test_multi_gpu_and_no_duration_inference(self):
        result = assess(Path(__file__).resolve().parents[1] / 'examples/synthetic-fleet.csv')
        self.assertEqual(result['gpu_count'], 2)
        self.assertEqual(result['gpus_with_reported_thermal_throttling'], 1)
        self.assertEqual(result['gpus'][0]['reported_thermal_throttle_sample_fraction'], 0.5)
        self.assertNotIn('lost_gpu_hours', result)

    def test_rejects_bad_evidence(self):
        for row in ['2026-10-01T10:00:00,g,70,400,0',
                    '2026-10-01T10:00:00Z,g,nan,400,0',
                    '2026-10-01T10:00:00Z,g,70,-1,0',
                    '2026-10-01T10:00:00Z,g,70,400,unknown']:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.run_data(HEADER + row)

    def test_duplicate_instant_different_offsets(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.run_data(HEADER + '2026-10-01T10:00:00Z,g,70,400,0\n2026-10-01T11:00:00+01:00,g,71,410,1\n')

    def test_empty(self):
        with self.assertRaises(ValueError):
            self.run_data(HEADER)

    def test_sort_and_irregular_cadence(self):
        result = self.run_data(HEADER + '2026-10-01T10:00:30Z,g,70,400,0\n2026-10-01T10:00:00Z,g,70,400,0\n2026-10-01T10:00:10Z,g,70,400,1\n')
        self.assertEqual(result['gpus'][0]['interval_seconds_min'], 10)
        self.assertEqual(result['gpus'][0]['interval_seconds_max'], 20)


if __name__ == '__main__':
    unittest.main()
