# ThermaCompute CrashLens

**Turn GPU job logs into a local, reviewable incident report.**

CrashLens scans saved UTF-8 logs for known failure signatures and attaches source line numbers and suggested next checks. It runs offline with Python's standard library: no account, API key, GPU, or production SSH access required.

**Status: experimental 0.2.0.** Tested against synthetic fixtures; not validated across production fleets. It identifies text patterns, not confirmed root causes, and does not fix jobs or control hardware.

## Try it in one minute

Requires Python 3.10 or newer.

```sh
git clone https://github.com/rohitcn-hub/thermacompute-crashlens.git
cd thermacompute-crashlens
python crashlens.py examples/synthetic.log --out demo-report
```

Open `demo-report/report.html` locally. The same directory contains Markdown and JSON.
[Preview the synthetic Markdown report](examples/sample-report/report.md).
No real customer data is included in the demo.

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

Inputs are limited to 20 MiB combined and must be UTF-8 text. There is no multiline traceback reconstruction, job/rank correlation, automatic remediation, or verified root-cause inference. Repeated matches are occurrences, not unique incidents. No matches means **insufficient evidence**, not a healthy system.

## Verify and contribute

```sh
python -m unittest discover -s tests -v
```

See [contribution guidance](CONTRIBUTING.md), [security guidance](SECURITY.md), and [architecture](ARCHITECTURE.md).
Please report missed signatures with a minimal synthetic example, expected result and Python version. Never submit credentials or private customer logs.

Licensed under [MIT](LICENSE). This release builds on the earlier ThermaCompute Incident Lens preview; CrashLens is the public product name for this repository.

## Optional: $80 GPU Efficiency Audit

[See the exact scope and request checklist](docs/thermal-audit.md) | [View a synthetic sample PDF](docs/ThermaCompute-Sample-Thermal-Audit.pdf). All sample measurements are invented. This is a one-time audit.

CrashLens remains free. If you also need a review of temperature, power and reported-throttling telemetry, email **vivaan.thermacompute@gmail.com** with your GPU model/count and CSV headers first.

We confirm data suitability and scope before payment. The audit provides supported findings, prioritized checks and a PDF with assumptions and limitations. It does not guarantee savings or include production changes. An audit is not required to use CrashLens and does not commit you to a subscription.

## Learn more

[Walkthrough: from GPU crash logs to a reviewable report](docs/CRASHLENS-WALKTHROUGH.md).
