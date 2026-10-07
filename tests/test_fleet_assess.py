import tempfile
import unittest
from pathlib import Path
from fleet_assess import assess, review_record

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

    def test_only_flagged_gpu_gets_recommendation(self):
        report = assess(Path(__file__).resolve().parents[1] / 'examples/synthetic-fleet.csv', 'synthetic')
        self.assertEqual(report['evidence_kind'], 'synthetic')
        self.assertEqual(len(report['recommendations']), 1)
        rec = report['recommendations'][0]
        self.assertEqual(rec['evidence']['thermal_evidence_rows'], [3])
        self.assertIsNone(rec['proposed_test']['hardware_change'])
        self.assertEqual(rec['outcome']['status'], 'not_tested')

    def review_fixture(self):
        report = assess(Path(__file__).resolve().parents[1] / 'examples/synthetic-fleet.csv', 'synthetic')
        feedback = {'recommendation_id': 'recommendation-1', 'reviewer': 'Synthetic example reviewer',
                    'decision': 'needs_evidence', 'useful_or_missing_check': 'Need comparable workload throughput'}
        return report, feedback

    def test_review_does_not_grant_execution_or_mutate_assessment(self):
        report, feedback = self.review_fixture()
        result = review_record(report, feedback)
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['evidence_kind'], 'synthetic')
        self.assertEqual(report['recommendations'][0]['outcome']['status'], 'not_tested')
        self.assertEqual(len(result['assessment_sha256']), 64)

    def test_invalid_reviewer_or_recommendation_rejected(self):
        for key, value in [('reviewer', ''), ('recommendation_id', 'missing'), ('decision', 'approved_for_execution')]:
            report, feedback = self.review_fixture()
            feedback[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                review_record(report, feedback)

    def test_tested_result_requires_measurements_and_learning(self):
        report, feedback = self.review_fixture()
        feedback.update(decision='tested', result='inconclusive')
        with self.assertRaises(ValueError):
            review_record(report, feedback)
        feedback.update(test_description='Synthetic review only', measurements='Two samples, no throughput', learning='Collect aligned throughput before intervention')
        self.assertEqual(review_record(report, feedback)['feedback']['result'], 'inconclusive')

    def test_untested_result_rejected(self):
        report, feedback = self.review_fixture()
        feedback['result'] = 'improved'
        with self.assertRaises(ValueError):
            review_record(report, feedback)

    def test_review_hash_changes_with_evidence(self):
        report, feedback = self.review_fixture()
        first = review_record(report, feedback)['assessment_sha256']
        report['gpus'][0]['temperature_c_max'] += 1
        self.assertNotEqual(first, review_record(report, feedback)['assessment_sha256'])


if __name__ == '__main__':
    unittest.main()
