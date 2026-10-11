"""Run the real CrashLens analyzer on clearly labeled synthetic examples."""
import argparse
import json
from pathlib import Path
import tempfile
import uuid

from crashlens import main as analyze_logs

SCENARIOS = {
    'oom': '2026-01-01T00:00:00Z INFO synthetic example\n2026-01-01T00:00:01Z CUDA out of memory\n2026-01-01T00:00:02Z Worker failed with error\n2026-01-01T00:00:03Z NCCL timeout\n',
    'thermal': '2026-01-01T00:00:00Z INFO synthetic example\n2026-01-01T00:00:01Z Thermal Throttling\n2026-01-01T00:00:02Z HW Slowdown\n',
    'unknown': 'INFO synthetic example\nINFO job stopped without a supported error signature\n',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, default='oom')
    parser.add_argument('--out', type=Path, help='New output folder; never overwritten')
    args = parser.parse_args(argv)
    out = args.out or Path('crashlens-demo-' + uuid.uuid4().hex[:12])
    # Only invented data enters the analyzer. No uploads, packages or GPU calls.
    with tempfile.TemporaryDirectory(prefix='crashlens-synthetic-') as temporary:
        source = Path(temporary) / 'synthetic.log'
        source.write_text(SCENARIOS[args.scenario], encoding='utf-8')
        analyze_logs([str(source), '--out', str(out)])
    notice = 'SYNTHETIC DEMO ONLY. Invented events; not customer evidence or proven causation.'
    report_path = out / 'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['demo'] = {'synthetic': True, 'scenario': args.scenario}
    report['warnings'].insert(0, notice)
    from crashlens import markdown, render_html
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (out / 'report.md').write_text(markdown(report), encoding='utf-8')
    (out / 'report.html').write_text(render_html(report), encoding='utf-8')
    print(notice)
    print('Open this report in your browser: ' + (out / 'report.html').resolve().as_uri())
    print('Feedback: Did you open the report? Name one useful or missing check.')
    print('https://github.com/rohitcn-hub/thermacompute-crashlens/issues/2')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
