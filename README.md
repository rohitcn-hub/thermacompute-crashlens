# ThermaCompute CrashLens

**Turn GPU job logs into a local, reviewable incident report.**

CrashLens scans saved UTF-8 logs for known failure signatures and attaches source line numbers and suggested next checks. It runs offline with Python's standard library: no account, API key, GPU, or production SSH access required.

**Status: experimental 0.3.0.** Tested against synthetic fixtures; not validated across production fleets. It identifies text patterns, not confirmed root causes, and does not fix jobs or control hardware.

## Multi-worker investigation — new in 0.3.0

```sh
python crashlens.py examples/distributed --out distributed-report
```

Open `distributed-report/report.html`. The synthetic example contains three matched messages and one candidate cross-rank relationship. No GPU, account, network connection or extra package is needed.

The report includes:

- A concise investigation brief and prioritized checks linked to individual evidence cards.
- A timeline with adjacent, best-effort-redacted source lines.
- Explicit `job=`, `job_id=`, `rank=`, `[rank0]`, `gpu=` and `gpu_uuid=` identifiers. No identity is inferred from filenames or propagated across lines.
- Candidate peer-failure-to-timeout relationships for the same explicit job label, different ranks and a preceding failure within 120 seconds. Only the nearest qualifying peer failure is linked. This is not verified causation, a measured stall or proof of the same job run/collective.
- Source aliases and SHA-256 fingerprints of decoded input text; original filenames are not included in reports.
- Self-contained HTML without scripts or external assets, plus Markdown and JSON (schema version 2).

Folders include immediate `.log` and `.txt` files only, sorted by path; other extensions and symlinks are skipped. Explicit symlink inputs and duplicate files are rejected. Limits: 128 files, 20 MiB combined and 5,000 matches. Reports never overwrite existing output directories.

Clock synchronization remains unverified. Missing/ambiguous job or rank IDs prevent correlation. Priorities are ordered by signature specificity, not a probability of root cause. Telemetry joins, baseline comparisons and financial estimates are not part of this release. The hosted browser demo remains the earlier fixed-example experience.

## Try CrashLens in your browser

**[Open the interactive synthetic demo](https://crashlens-demo.rohitc-n474269.chatgpt.site)** — no Python, GPU or installation needed.

Choose one of three invented examples, analyze it, select a finding to inspect its source line and suggested next check, and download the demo report. Includes an inconclusive example to show why no matches does not mean a healthy system.

The browser demo accepts no uploads or custom logs. It runs fixed examples using the CLI's signature definitions; it is not the full CLI or evidence of production validation. Browser exploration and completed local CLI trials are separate.

## See the result before running anything

**[Open the sample report](examples/sample-report/report.md)** — no installation or sign-up required. It uses [five lines of synthetic input](examples/synthetic.log), not customer data.

| Evidence in this demo | Suggested next check |
| --- | --- |
| Line 3: CUDA out of memory | Inspect memory use in the affected worker. |
| Line 4: worker failure | Inspect that worker's exception and peer logs. |
| Line 5: collective timeout | Check earlier worker errors before treating the timeout as the cause. |

These are three matched messages, not three proven root causes. Their order does not establish causation or prove a thermal problem. [Read the example investigation](docs/synthetic-walkthrough.md).

## Run the free synthetic demo

Requires Python 3.10 or newer.

```sh
git clone https://github.com/rohitcn-hub/thermacompute-crashlens.git
cd thermacompute-crashlens
python crashlens.py examples/synthetic.log --out demo-report
```

Open `demo-report/report.html` locally. The same directory contains Markdown and JSON.
[Preview the synthetic Markdown report](examples/sample-report/report.md).
No real customer data is included in the demo. Expected terminal output:

```text
matches_found: 3 matches. Reports written locally. Review before sharing.
```

Double-click `report.html` in the `demo-report` folder to open it in your browser.

### If the first run gets stuck

- **Python command missing or too old:** check `python --version`. Use Python 3.10+. On macOS/Linux, try `python3`; on Windows, try `py -3` in place of `python`.
- **No Git installed:** use GitHub's **Code → Download ZIP**, extract it, then open a terminal in the extracted folder.
- **Output folder already exists:** run again with a new name, such as `--out demo-report-2`. Existing reports are deliberately not overwritten.
- **No report found:** check the terminal for an error and confirm you ran the command from the folder containing `crashlens.py`.

### Tell us where you got to

[Use the short trial-feedback form](https://github.com/rohitcn-hub/thermacompute-crashlens/issues/new?template=trial-feedback.yml), [comment in issue #2](https://github.com/rohitcn-hub/thermacompute-crashlens/issues/2), or email **vivaan.thermacompute@gmail.com**:

1. Did the command finish?
2. Did you open `report.html`?
3. Did it give you a useful next check? What was missing?

If it failed, include your OS, Python version and the error from the **synthetic demo**. No production logs, GPU, account or payment are needed for this trial.

For your own saved logs:

```sh
python crashlens.py worker-0.log worker-1.log --out my-report
```

Output directories must be new. The original one-file command still works and writes to `crashlens-report/`; it no longer overwrites `crash_report.md`.

## What you get

- GPU allocation failures and host OOM events classified separately.
- Collective timeouts, missing Python dependencies, worker failures, NVIDIA Xid messages, and explicit thermal/NVLink messages.
- Hardware slowdown and lost-GPU messages kept separate from unproven thermal or NVLink causes.
- Source aliases and line numbers, occurrence counts, and evidence-linked next checks.
- UTC ordering only when all matched events have timezone-aware timestamps; otherwise input order.
- JSON, Markdown and static HTML reports with best-effort secret masking.

A generic `NCCL WARN` is not automatically a timeout. A thermal message is not proof of lost performance or savings.

## Privacy and limits

The CLI makes no network requests, installs nothing, and changes no GPU settings. It reads only the input files you specify and writes reports locally.

Logs can contain prompts, secrets, paths or identifying information. Masking is incomplete: review reports before sharing. Output files are not encrypted and inherit your system's permissions. Do not upload production logs to public issues.

Inputs are limited to 20 MiB combined and must be UTF-8 text. There is no multiline traceback reconstruction, automatic remediation, or verified root-cause inference. Job/rank correlation is limited to explicit identifiers and the documented 120-second window. Repeated matches are occurrences, not unique incidents. No matches means **insufficient evidence**, not a healthy system.

## Verify and contribute

```sh
python -m unittest discover -s tests -v
```

See [contribution guidance](CONTRIBUTING.md), [security guidance](SECURITY.md), and [architecture](ARCHITECTURE.md).
Please report missed signatures with a minimal synthetic example, expected result and Python version. Never submit credentials or private customer logs.

Licensed under [MIT](LICENSE). This release builds on the earlier ThermaCompute Incident Lens preview; CrashLens is the public product name for this repository.

## Optional executive review

CrashLens remains free and MIT licensed. The separate **$800 Executive Thermal Architecture Audit** provides a scoped review of agreed NVML/vLLM exports, evidence tables and a validation plan. Scope, delivery and data handling are agreed before payment. No guaranteed savings or production changes.

[Executive audit details](https://thermacompute-ai.rohitc-n474269.chatgpt.site/#report).

## Learn more

[Walkthrough: from GPU crash logs to a reviewable report](docs/CRASHLENS-WALKTHROUGH.md).
