"""Experimental, offline fleet telemetry assessment. Python 3.10+, stdlib only."""
import argparse
import csv
import json
import math
import hashlib
import io
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {'timestamp', 'gpu_id', 'temperature_c', 'power_w', 'thermal_throttle'}


def assess(path, evidence_kind='unspecified'):
    if evidence_kind not in ('synthetic', 'operator_export', 'unspecified'):
        raise ValueError('Invalid evidence kind')
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('Input exceeds 20 MiB experimental limit')
    with path.open('rb') as source:
        raw = source.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError('Input exceeds 20 MiB experimental limit')
    groups = defaultdict(list)
    seen = set()
    with io.StringIO(raw.decode('utf-8-sig'), newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Missing or duplicate column headers')
        if not REQUIRED.issubset(reader.fieldnames):
            raise ValueError('Required columns: ' + ', '.join(sorted(REQUIRED)))
        for line, row in enumerate(reader, 2):
            try:
                if None in row or any(row[k] is None for k in REQUIRED):
                    raise ValueError('Malformed CSV row')
                gpu = row['gpu_id'].strip()
                if not gpu:
                    raise ValueError('gpu_id is empty')
                timestamp = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    raise ValueError('timestamp needs a UTC offset')
                timestamp = timestamp.astimezone(timezone.utc)
                temp, power = float(row['temperature_c']), float(row['power_w'])
                if not math.isfinite(temp) or not math.isfinite(power) or power < 0:
                    raise ValueError('Nonfinite metric or negative power')
                flag = row['thermal_throttle'].strip()
                if flag not in ('0', '1'):
                    raise ValueError('thermal_throttle must be explicit 0 or 1')
                key = (gpu, timestamp)
                if key in seen:
                    raise ValueError('Duplicate GPU/timestamp')
                seen.add(key)
                groups[gpu].append((timestamp, temp, power, int(flag), line))
            except (ValueError, TypeError) as error:
                raise ValueError(f'Row {line}: {error}') from error
    if not groups:
        raise ValueError('No telemetry rows')
    results = []
    for gpu, rows in sorted(groups.items()):
        rows.sort()
        intervals = [(b[0] - a[0]).total_seconds() for a, b in zip(rows, rows[1:])]
        count = sum(r[3] for r in rows)
        results.append({
            'gpu_id': gpu, 'samples': len(rows),
            'window_start': rows[0][0].isoformat(), 'window_end': rows[-1][0].isoformat(),
            'temperature_c_max': max(r[1] for r in rows),
            'power_w_max': max(r[2] for r in rows),
            'reported_thermal_throttle_samples': count,
            'reported_thermal_throttle_sample_fraction': count / len(rows),
            'thermal_evidence_rows': [r[4] for r in rows if r[3]],
            'interval_seconds_min': min(intervals) if intervals else None,
            'interval_seconds_max': max(intervals) if intervals else None,
            'next_check': ('Correlate reported thermal throttling with workload throughput, clocks and cooling telemetry in the same window; review device-specific limits before proposing a supervised experiment.' if count else 'No thermal throttle flag in these samples. Check collection coverage and other slowdown reasons before drawing conclusions.'),
        })
    recommendations = []
    for item in results:
        if not item['reported_thermal_throttle_samples']:
            continue
        recommendations.append({
            'id': f'recommendation-{len(recommendations) + 1}',
            'gpu_id': item['gpu_id'],
            'evidence': {key: item[key] for key in ('window_start', 'window_end', 'samples', 'thermal_evidence_rows', 'reported_thermal_throttle_samples')},
            'hypothesis': 'Reported thermal throttling may coincide with reduced workload performance; causation and impact are unverified.',
            'alternatives': ['Workload or batch changes', 'Other slowdown reasons', 'Incorrect signal mapping or incomplete sampling'],
            'missing_context': ['GPU model and documented signal mapping', 'Workload/run identifier and comparable baseline', 'Timestamp-aligned throughput with units, clocks and cooling readings', 'Expected inventory and sampling cadence'],
            'proposed_test': {'kind': 'read-only correlation', 'instruction': item['next_check'],
                              'hardware_change': None,
                              'baseline': 'Operator selects a comparable workload and observation window.',
                              'success_criterion': 'Operator can reproduce whether the flag and performance change coincide; a negative or inconclusive finding is valid.'},
            'approval': {'status': 'not_requested', 'operator': None},
            'future_execution_requirements': ['Explicit authorized operator approval', 'One bounded change and test group', 'Predeclared metric, baseline and success threshold', 'Device-specific limits, stop conditions and rollback reviewed by operator'],
            'outcome': {'status': 'not_tested', 'measurements': None, 'learning': None},
        })
    return {'schema_version': 2, 'mode': 'read-only offline assessment',
            'evidence_kind': evidence_kind,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'units': {'temperature_c': 'Celsius', 'power_w': 'watts', 'thermal_throttle': 'explicit thermal-specific flag 0 or 1'},
            'gpu_count': len(results), 'gpus_with_reported_thermal_throttling': sum(r['reported_thermal_throttle_samples'] > 0 for r in results),
            'limitations': ['Sample fractions are not duration, performance loss or recoverable capacity.',
                            'No universal temperature threshold is applied.',
                            'Sampling gaps and missing GPUs cannot be inferred without an expected inventory and cadence.',
                            'No hardware changes, network access, savings estimates or proven root causes.'],
            'gpus': results, 'recommendations': recommendations}


def review_record(report, feedback):
    """Record a human statement without treating it as independently verified."""
    if report.get('schema_version') != 2:
        raise ValueError('Review requires a schema version 2 assessment')
    if not isinstance(feedback, dict):
        raise ValueError('Feedback must be a JSON object')
    for key in ('recommendation_id', 'reviewer', 'decision', 'useful_or_missing_check'):
        if not isinstance(feedback.get(key), str) or not feedback[key].strip():
            raise ValueError(f'Feedback needs a nonempty {key}')
    if feedback['decision'] not in ('accepted_for_investigation', 'rejected', 'needs_evidence', 'tested'):
        raise ValueError('Invalid review decision')
    if feedback['recommendation_id'] not in {r['id'] for r in report['recommendations']}:
        raise ValueError('Unknown recommendation ID')
    if feedback['decision'] == 'tested':
        if feedback.get('result') not in ('improved', 'worsened', 'unchanged', 'inconclusive'):
            raise ValueError('A tested review needs a result')
        for key in ('test_description', 'measurements', 'learning'):
            if not isinstance(feedback.get(key), str) or not feedback[key].strip():
                raise ValueError(f'A tested review needs {key}')
    elif any(key in feedback for key in ('result', 'measurements', 'test_description')):
        raise ValueError('Measurements and results require decision=tested')
    allowed = ('recommendation_id', 'reviewer', 'decision', 'useful_or_missing_check', 'result', 'measurements', 'test_description', 'learning')
    return {'schema_version': 1, 'record_type': 'operator_statement',
            'recorded_at': datetime.now(timezone.utc).isoformat(),
            'assessment_sha256': hashlib.sha256(json.dumps(report, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            'source_sha256': report['source_sha256'], 'evidence_kind': report['evidence_kind'],
            'verification': 'Self-reported; reviewer identity, authorization and measurements are not independently verified.',
            'execution_authorized': False,
            'feedback': {k: feedback[k] for k in allowed if k in feedback}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file', nargs='?')
    parser.add_argument('--out', default='fleet-report.json')
    parser.add_argument('--evidence-kind', choices=['synthetic', 'operator_export', 'unspecified'], default='unspecified')
    parser.add_argument('--review', metavar='ASSESSMENT_JSON')
    parser.add_argument('--feedback', metavar='FEEDBACK_JSON')
    args = parser.parse_args()
    try:
        if args.review:
            if args.csv_file or not args.feedback:
                raise ValueError('Use --review REPORT --feedback FEEDBACK --out NEW_FILE, without CSV input')
            with open(args.review, encoding='utf-8') as handle:
                assessment = json.load(handle)
            with open(args.feedback, encoding='utf-8') as handle:
                feedback = json.load(handle)
            report = review_record(assessment, feedback)
        else:
            if not args.csv_file or args.feedback:
                raise ValueError('Supply a telemetry CSV, or use --review with --feedback')
            report = assess(args.csv_file, args.evidence_kind)
        with open(args.out, 'x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write('\n')
    except (ValueError, OSError, csv.Error, KeyError, TypeError) as error:
        parser.exit(2, f'Assessment failed: {error}\n')
    print(f"Written locally: {args.out}. Review identifiers before sharing. No hardware actions executed.")


if __name__ == '__main__':
    main()
