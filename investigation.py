"""Deterministic incident investigation; standard library only, no network or GPU access."""
import datetime as dt
import hashlib
import html
import re

IDENTITY = {key: re.compile(pattern, re.I) for key, pattern in {
    'job': r'\b(?:job_id|job)\s*[=:]\s*([\w.-]{1,80})(?![\w.-])',
    'rank': r'\brank\s*[=: ]\s*(\d{1,8})\b|\[rank(\d{1,8})\]',
    'gpu': r'\b(?:gpu_uuid|gpu)\s*[=:]\s*([\w.-]{1,80})(?![\w.-])',
}.items()}


def enrich(report, texts, redact):
    """Never propagate identifiers from another line or infer identity from filenames."""
    sources = [text.splitlines() for text in texts]
    report['schema_version'] = 2
    report['sources'] = [{'id': f'input-{i}', 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                          'lines': len(text.splitlines()), 'fingerprint_basis': 'decoded UTF-8 text, BOM removed by CLI'}
                         for i, text in enumerate(texts, 1)]
    for number, event in enumerate(report['events'], 1):
        source = sources[int(event['source'].split('-')[1])-1]
        raw = source[event['line']-1]
        event['id'] = f'E{number:04d}'
        event['identity'] = {}
        for key, pattern in IDENTITY.items():
            values = {next(g for g in m.groups() if g is not None) for m in pattern.finditer(raw)}
            # Multiple identities on a line are ambiguous: do not choose one.
            if len(values) == 1:
                event['identity'][key] = redact(values.pop())
        event['context'] = [{'line': j+1, 'text': redact(source[j])[:2000]}
                            for j in range(max(0,event['line']-2), min(len(source),event['line']+1))]
    report['coverage'] = {
        'timestamped_matches': sum(bool(e['timestamp']) for e in report['events']),
        'job_identified_matches': sum('job' in e['identity'] for e in report['events']),
        'rank_identified_matches': sum('rank' in e['identity'] for e in report['events']),
        'clock_synchronization': 'unverified',
    }
    # Match only explicit same-job, different-rank events in a bounded time window.
    # Select nearest preceding failure, not every possible edge (bounded report size).
    failures = {}
    links = []
    timed = sorted((e for e in report['events'] if e['timestamp']),
                   key=lambda e: dt.datetime.fromisoformat(e['timestamp']))
    for event in timed:
        identity = event['identity']; job, rank = identity.get('job'), identity.get('rank')
        if job is None or rank is None:
            continue
        when = dt.datetime.fromisoformat(event['timestamp'])
        candidates = failures.setdefault(job, {})
        if event['rule'] == 'nccl_timeout':
            options = [e for r,e in candidates.items() if r != rank and
                       0 < (when-dt.datetime.fromisoformat(e['timestamp'])).total_seconds() <= 120]
            if options:
                first = max(options, key=lambda e: dt.datetime.fromisoformat(e['timestamp']))
                links.append({'from': first['id'], 'to': event['id'], 'job': job,
                              'observed_delta_seconds': (when-dt.datetime.fromisoformat(first['timestamp'])).total_seconds(),
                              'classification': 'candidate_relationship',
                              'hypothesis': 'A peer failure may have prevented collective participation.',
                              'limitation': 'Same job label and timestamp proximity do not prove the same job run, collective or cause. Clocks are unverified; delta is not stall duration.',
                              'next_check': 'Verify job-run identity and clock offsets; compare collective sequence IDs and peer Flight Recorder traces.'})
        if event['rule'] in {'gpu_oom','host_oom','worker_exit','triton_shared_memory','gpu_lost'}:
            candidates[rank] = event
    report['relationships'] = links
    counts = report['counts']
    priorities = []
    for rule in ['gpu_oom','host_oom','triton_shared_memory','missing_module','gpu_xid','gpu_lost','worker_exit','thermal_message','hardware_slowdown','nvlink_message','nccl_timeout']:
        matched = [e for e in report['events'] if e['rule'] == rule]
        if matched:
            priorities.append({'priority': len(priorities)+1, 'title': matched[0]['title'],
                               'evidence_ids': [e['id'] for e in matched], 'next_check': matched[0]['next_check'],
                               'basis': 'Investigation order by signature specificity, not probability or root-cause ranking.'})
    report['priorities'] = priorities
    report['summary'] = (f"{len(report['events'])} signature matches across {len(texts)} sources; "
                         f"{len(links)} cross-rank candidate relationships. No root cause confirmed."
                         if counts else 'Insufficient evidence: no recognized signatures. This is not a health certificate.')
    return report


def investigation_markdown(report):
    lines = ['## Investigation brief', '', report['summary'], '', '### Evidence coverage',
             f"Clock synchronization: {report['coverage']['clock_synchronization']}",
             f"Explicit job / rank matches: {report['coverage']['job_identified_matches']} / {report['coverage']['rank_identified_matches']}",
             '', '### Prioritized checks (not causal rankings)']
    for item in report['priorities']:
        lines += [f"{item['priority']}. {item['title']} — {item['next_check']}",
                  '   Evidence: '+', '.join(item['evidence_ids'])]
    lines += ['', '### Cross-rank candidates']
    for link in report['relationships']:
        lines += [f"- {link['from']} → {link['to']}: {link['hypothesis']}",
                  '  '+link['limitation'], '  Next check: '+link['next_check']]
    if not report['relationships']:
        lines += ['No supported cross-rank candidates. Missing identities or timing can prevent correlation.']
    lines += ['', '### Source fingerprints']
    lines += [f"- {s['id']}: {s['sha256']} ({s['lines']} lines; {s['fingerprint_basis']})" for s in report['sources']]
    return '\n'.join(lines)+'\n'


def render(report):
    esc = lambda value: html.escape(str(value), quote=True)
    def evidence_links(ids):
        return ' '.join(f'<a href="#{esc(i)}">{esc(i)}</a>' for i in ids)
    priorities = ''.join(f'<article class="check"><span class="eyebrow">CHECK {p["priority"]:02d}</span><h3>{esc(p["title"])}</h3><p>{esc(p["next_check"])}</p><p>{evidence_links(p["evidence_ids"])}</p></article>' for p in report['priorities'])
    relationships = ''.join(f'<article class="check"><span class="eyebrow">CANDIDATE · NOT CONFIRMED</span><h3>{evidence_links([r["from"],r["to"]])}</h3><p>{esc(r["hypothesis"])}</p><p>{esc(r["observed_delta_seconds"])}s observed timestamp difference</p><p class="muted">{esc(r["limitation"])}</p><p><b>Verify:</b> {esc(r["next_check"])}</p></article>' for r in report['relationships'])
    events = ''
    for e in report['events']:
        identity = ' · '.join(f'{k}={v}' for k,v in e['identity'].items()) or 'Identity unavailable'
        context = '\n'.join(f'{c["line"]:>6}  {c["text"]}' for c in e['context'])
        events += f'<article id="{e["id"]}" class="event"><div class="eyebrow">{e["id"]} / {esc(e["source"])}:{e["line"]}</div><h3>{esc(e["title"])}</h3><p>{esc(e["timestamp"] or "Timestamp unavailable")}<br>{esc(identity)}</p><pre>{esc(e["evidence"])}</pre><details><summary>Adjacent source lines</summary><pre>{esc(context)}</pre></details><p><b>Next check:</b> {esc(e["next_check"])}</p></article>'
    sources = ''.join(f'<tr><td>{s["id"]}</td><td>{s["lines"]}</td><td><code>{s["sha256"]}</code></td></tr>' for s in report['sources'])
    warnings = ''.join('<li>'+esc(w)+'</li>' for w in report['warnings'])
    cov=report['coverage']; total=len(report['events'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>CrashLens · Incident investigation</title><style>
:root{color-scheme:light;--ink:#182137;--muted:#59647a;--blue:#242bb4;--line:#dce0e9}*{box-sizing:border-box}body{margin:0;background:#f2f3f7;color:var(--ink);font:16px/1.65 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:32px}header{border-top:5px solid var(--blue);padding:32px 0}h1{font-size:clamp(32px,5vw,58px);letter-spacing:-.05em;line-height:1.1;margin:18px 0}h2{font-size:26px;margin:36px 0 18px}h3{font-size:18px;margin:10px 0}p{margin:12px 0}.eyebrow{font:12px/1.5 ui-monospace,monospace;letter-spacing:.08em;color:var(--blue)}.muted{color:var(--muted)}nav{display:flex;gap:20px;flex-wrap:wrap;padding:16px 0;border-block:1px solid var(--line)}a{color:var(--blue);text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #b44a00;outline-offset:4px}.stats,.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.stats>div,.check,.event,.notice{background:white;border:1px solid var(--line);padding:22px;border-radius:10px}.stats{margin:24px 0}.stats strong{display:block;font-size:32px}.stats span{color:var(--muted);font-size:14px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.event{margin:16px 0;scroll-margin-top:20px}.event:target{border:2px solid var(--blue)}pre{background:#111b30;color:#e9edf8;padding:16px;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.8 ui-monospace,monospace;border-radius:6px}summary{cursor:pointer;padding:12px 0}table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{text-align:left;padding:12px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}th:nth-child(3){width:65%}.notice{border-left:4px solid #b17720}footer{padding:24px 0;font-size:13px;color:var(--muted)}@media(max-width:640px){main{padding:18px}.stats,.grid{grid-template-columns:1fr}.event,.check{padding:18px}td,th{padding:6px;font-size:12px}}@media print{body{background:white}main{max-width:none;padding:0}nav{display:none}.check,.event{break-inside:avoid}pre{background:#eee;color:black}}
</style></head><body><main><header><div class="eyebrow">THERMACOMPUTE / CRASHLENS / LOCAL INVESTIGATION</div><h1>Evidence before assumptions.</h1><p>'''+esc(report['summary'])+'''</p><p class="muted">Experimental · free and open source · no uploads · no automatic changes</p></header><nav aria-label="Report sections"><a href="#checks">Prioritized checks</a><a href="#relationships">Cross-rank candidates</a><a href="#timeline">Evidence timeline</a><a href="#method">Coverage &amp; method</a></nav>'''+f'<div class="stats"><div><strong>{report["input_count"]}</strong><span>Source files</span></div><div><strong>{total}</strong><span>Signature matches, not incidents</span></div><div><strong>{cov["timestamped_matches"]}/{total}</strong><span>Matches with timezone-aware timestamps</span></div></div>'+'''<div class="notice">Clock synchronization is unverified. Relationships are investigation leads, not proof of causation. This report does not measure financial loss or hardware lifespan.</div><section id="checks"><h2>01 / What to check next</h2><p class="muted">Ordered by signature specificity, not causal probability.</p><div class="grid">'''+(priorities or '<p>No supported checks from these signatures. Inspect additional evidence.</p>')+'''</div></section><section id="relationships"><h2>02 / Across workers</h2><div class="grid">'''+(relationships or '<p>No supported cross-rank candidates. Explicit job/rank IDs and usable timestamps are required; absence is inconclusive.</p>')+'''</div></section><section id="timeline"><h2>03 / Evidence timeline</h2><p class="muted">'''+esc(report['ordering'])+'</p>'+events+'''</section><section id="method"><h2>04 / Coverage &amp; method</h2><ul>'''+warnings+'''</ul><p>Correlations require the same explicit job label, different explicit ranks and a preceding recognized peer failure within 120 seconds. Only the nearest qualifying peer failure is linked. Missing, conflicting or unrecognized identities remain unknown. Run IDs and collective IDs require manual verification.</p><table><thead><tr><th>Source</th><th>Lines</th><th>SHA-256 of decoded UTF-8 text</th></tr></thead><tbody>'''+sources+'''</tbody></table><p class="muted">Fingerprints cover decoded text after CLI BOM removal, not original file bytes. Filenames are replaced with input-order aliases. Best-effort masking is not anonymization; review before sharing.</p></section><footer>CrashLens '''+esc(report['version'])+''' · Python standard library · report contains no scripts or remote assets</footer></main></body></html>'''
