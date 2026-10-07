"""Experimental, offline fleet telemetry assessment. Python 3.10+, stdlib only."""
import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {'timestamp', 'gpu_id', 'temperature_c', 'power_w', 'thermal_throttle'}


def assess(path):
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('Input exceeds 20 MiB experimental limit')
    groups = defaultdict(list)
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as handle:
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
                groups[gpu].append((timestamp, temp, power, int(flag)))
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
            'interval_seconds_min': min(intervals) if intervals else None,
            'interval_seconds_max': max(intervals) if intervals else None,
            'next_check': ('Correlate reported thermal throttling with workload throughput, clocks and cooling telemetry in the same window; review device-specific limits before proposing a supervised experiment.' if count else 'No thermal throttle flag in these samples. Check collection coverage and other slowdown reasons before drawing conclusions.'),
        })
    return {'schema_version': 1, 'mode': 'read-only offline assessment',
            'gpu_count': len(results), 'gpus_with_reported_thermal_throttling': sum(r['reported_thermal_throttle_samples'] > 0 for r in results),
            'limitations': ['Sample fractions are not duration, performance loss or recoverable capacity.',
                            'No universal temperature threshold is applied.',
                            'Sampling gaps and missing GPUs cannot be inferred without an expected inventory and cadence.',
                            'No hardware changes, network access, savings estimates or proven root causes.'],
            'gpus': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file')
    parser.add_argument('--out', default='fleet-report.json')
    args = parser.parse_args()
    try:
        report = assess(args.csv_file)
        with open(args.out, 'x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write('\n')
    except (ValueError, OSError, csv.Error) as error:
        parser.exit(2, f'Assessment failed: {error}\n')
    print(f"Assessed {report['gpu_count']} GPUs. Open {args.out}. Review identifiers before sharing.")


if __name__ == '__main__':
    main()
