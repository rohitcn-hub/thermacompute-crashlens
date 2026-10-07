"""CrashLens 0.2.0: offline, heuristic log triage. Python 3.10+."""
import argparse
import collections
import datetime as dt
import html
import json
from pathlib import Path
import re

VERSION = '0.2.0'
MAX_BYTES = 20 * 1024 * 1024
RULES = [
 ('gpu_oom', r'(?:CUDA out of memory|torch\.cuda\.OutOfMemoryError)', 'GPU allocation failure reported', 'Inspect memory usage and allocation context on the affected worker; distinguish model loading, cache allocation and CUDA graph capture. Do not assume that reducing one flag fixes all OOMs.'),
 ('triton_shared_memory', r'\bOutOfResources:\s*out of resource:\s*shared memory\b', 'Kernel shared-memory limit reported', 'Compare the reported required shared memory with the device limit and identify the failing kernel, GPU architecture and Triton/framework versions. Review upstream support and kernel configuration; this is not evidence of exhausted GPU VRAM or thermal throttling. Validate any configuration change on a small reproduction before production.'),
 ('host_oom', r'(?:Out of memory: Killed process|oom-kill:|invoked oom-killer)', 'Host OOM event reported', 'Check host RAM, container memory limits and kernel logs. A process exit alone does not establish GPU OOM.'),
 ('nccl_timeout', r'(?:Watchdog caught collective operation timeout|NCCL[^\n]{0,120}(?:timed out|timeout))', 'Collective timeout reported', 'Inspect other ranks for earlier failures. The rank reporting a timeout is not necessarily the culprit. Consider existing PyTorch Flight Recorder evidence.'),
 ('missing_module', r"ModuleNotFoundError: No module named", 'Python dependency missing', 'Check the active interpreter and installed environment against the deployment requirements. Do not install unreviewed packages automatically.'),
 ('gpu_xid', r'NVRM: Xid\s*\(', 'NVIDIA Xid event reported', 'Look up the Xid code in NVIDIA documentation and correlate with driver and job logs. One Xid does not prove defective hardware.'),
 ('thermal_message', r'(?:Thermal Throttling|temperature exceeds)', 'Thermal-related message reported', 'Confirm sensor readings, thresholds and throttle reasons in hardware telemetry. A text match does not establish clock loss, energy waste or financial impact.'),
 ('hardware_slowdown', r'HW Slowdown', 'Hardware slowdown message reported', 'Check the reported slowdown reason. This message alone does not establish thermal throttling.'),
 ('nvlink_message', r'NVLink[^\n]{0,120}error', 'NVLink error message reported', 'Correlate with driver and fabric diagnostics; this signature alone does not identify a failed component.'),
 ('gpu_lost', r'GPU is lost', 'GPU unavailable message reported', 'Check driver and hardware logs. This does not establish an NVLink failure.'),
 ('worker_exit', r'(?:Worker failed with error|Engine core initialization failed|ChildFailedError|Worker \(pid:\s*\d+\) exited unexpectedly|Segmentation fault)', 'Worker or engine failure reported', 'Find the underlying exception in this worker and its peers. This message may be a consequence rather than the initial error.')
]
RULES = [(i, re.compile(p, re.I), t, n) for i,p,t,n in RULES]
STAMP = re.compile(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?')

def redact(text):
    text = re.sub(r'(?i)(Bearer\s+)\S+', r'\1[REDACTED]', text)
    text = re.sub(r'''(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)''', r'\1[REDACTED]', text)
    return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', text)

def timestamp(line):
    m = STAMP.search(line)
    if not m:
        return None
    try:
        value = dt.datetime.fromisoformat(m[0].replace('Z', '+00:00'))
        return value.astimezone(dt.timezone.utc).isoformat() if value.tzinfo else None
    except ValueError:
        return None

def analyze(texts):
    """Input strings in supplied file order; no filenames or absolute paths exported."""
    events, lines = [], 0
    for number, text in enumerate(texts, 1):
        for line_no, line in enumerate(text.splitlines(), 1):
            lines += 1
            for rule_id, pattern, title, next_check in RULES:
                if pattern.search(line):
                    events.append(dict(source=f'input-{number}', line=line_no,
                        timestamp=timestamp(line), rule=rule_id, title=title,
                        evidence=redact(line)[:2000], next_check=next_check))
    warnings = ['Heuristic signature matches, not confirmed root causes or a health certificate.',
                'Redaction is best effort. Review all output before sharing; paths, hostnames and other secrets may remain.',
                'No-event results do not mean a healthy system. Only listed signatures are recognized.',
                'Clock synchronization and log completeness cannot be verified from these files.']
    if events and all(e['timestamp'] for e in events):
        events.sort(key=lambda e:e['timestamp'])
        ordering = 'UTC timestamp order (clock synchronization unverified)'
    else:
        ordering = 'Input file and line order; global chronology unavailable'
        warnings.append('Some events lack full timezone-aware timestamps. No global ordering or root-cause inference performed.')
    counts = collections.Counter(e['rule'] for e in events)
    return dict(version=VERSION, input_count=len(texts), lines_scanned=lines,
        ordering=ordering, status='matches_found' if events else 'insufficient_evidence',
        counts=dict(counts), events=events, warnings=warnings)

def markdown(report):
    out = ['# ThermaCompute CrashLens', '', f"Version {VERSION} — local heuristic triage", '',
           f"Status: {report['status']}", f"Lines scanned: {report['lines_scanned']}",
           f"Ordering: {report['ordering']}", '', '## Limitations']
    out += ['- '+w for w in report['warnings']]
    out += ['', '## Signature counts (not unique incident counts)']
    out += [f'- {k}: {v}' for k,v in report['counts'].items()] or ['- No supported signatures found.']
    for event in report['events']:
        out += ['', '## '+event['title'], f"Source: {event['source']}:{event['line']} | {event['timestamp'] or 'time unknown'}", '',
                'Evidence:', '']
        out += ['    '+s for s in event['evidence'].splitlines()]
        out += ['', 'Next check: '+event['next_check']]
    return '\n'.join(out)+'\n'

def render_html(report):
    # Escape every log byte; no JS, remote assets or external requests.
    body = html.escape(markdown(report))
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>CrashLens report</title><style>body{background:#081421;color:#dce8f5;font:16px/1.65 system-ui;margin:0;padding:clamp(20px,5vw,70px)}main{max-width:1000px;margin:auto}header{color:#42d3e8;letter-spacing:.12em}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#102235;border:1px solid #26415b;border-radius:16px;padding:24px;font:14px/1.7 ui-monospace,monospace}@media print{body,pre{background:white;color:black}}</style><main><header>THERMACOMPUTE / CRASHLENS</header><h1>Evidence before assumptions.</h1><p>Offline report · no automatic fixes · review before sharing</p><pre>'''+body+'</pre></main></html>'

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs', nargs='+', type=Path)
    p.add_argument('--out', type=Path, default=Path('crashlens-report'), help='New output directory (default: crashlens-report); refuses overwrite')
    args = p.parse_args(argv)
    try:
        data, total = [], 0
        for path in args.logs:
            if not path.is_file():
                raise ValueError('Each input must be a regular file.')
            with path.open('rb') as stream:
                raw = stream.read(MAX_BYTES-total+1)
            total += len(raw)
            if total > MAX_BYTES:
                raise ValueError('Combined inputs exceed the 20 MiB limit.')
            if b'\x00' in raw:
                raise ValueError('Binary input is unsupported.')
            data.append(raw.decode('utf-8-sig', errors='strict'))
        report = analyze(data)
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        (args.out/'report.md').write_text(markdown(report), encoding='utf-8')
        (args.out/'report.html').write_text(render_html(report), encoding='utf-8')
    except (OSError, UnicodeError, ValueError) as exc:
        p.exit(2, f'Input/output error: {exc}\n')
    print(f"{report['status']}: {len(report['events'])} matches. Reports written locally. Review before sharing.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
