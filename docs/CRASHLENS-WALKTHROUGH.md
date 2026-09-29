# From GPU crash logs to a reviewable incident report
*ThermaCompute CrashLens 0.2.0 · experimental · AI-assisted development and writing*

A failed GPU job can leave several different messages: an allocation error, a worker exit, and a later collective timeout. Collecting those messages is useful. Claiming that the last message proves the root cause is not.

CrashLens is a free, MIT-licensed Python tool for the first step: collect known failure signatures from saved logs into a local report with source line numbers and suggested checks.

## Try the synthetic example
Requires Python 3.10+. No GPU or API key is required.

```sh
git clone https://github.com/rohitcn-hub/thermacompute-crashlens.git
cd thermacompute-crashlens
python crashlens.py examples/synthetic.log --out demo-report
```

Open demo-report/report.html locally, or read the JSON and Markdown versions.
[See the sample report](../examples/sample-report/report.md).

## Three distinctions worth preserving
1. GPU allocation failure and host OOM are different signatures.
2. A generic NCCL warning is not necessarily a timeout.
3. A lost GPU does not, by itself, establish an NVLink failure.

CrashLens preserves those distinctions. It provides evidence to investigate, not an automatic diagnosis. Repeated matches count as occurrences, not distinct incidents. When timestamps are incomplete, it keeps input order instead of inventing a global timeline.

## What stays local
The CLI reads the files you specify and writes a new report directory. It makes no network requests, installs no dependencies and changes no GPU settings. Reports are not encrypted. Best-effort masking does not guarantee removal of secrets; review every report before sharing.

## What we have verified
The 0.2.0 release passed 18 local regression tests against synthetic fixtures, covering classification, redaction examples, HTML escaping, timestamps, malformed input and overwrite protection. This is not production fleet validation or a speed benchmark.

## Help make the next release useful
Try a saved log locally. Did the report surface useful evidence? Did it misclassify a line? [Open an issue](https://github.com/rohitcn-hub/thermacompute-crashlens/issues) with a minimal invented reproduction and expected behavior. Do not attach private production logs.

## When a hardware audit is relevant
For separate temperature, power and reported-throttling questions, ThermaCompute offers an $80 GPU Efficiency Audit. We confirm CSV suitability and scope before payment. Deliverables are supported findings, prioritized checks and a PDF explaining assumptions and limitations; savings are not guaranteed.

Email **vivaan.thermacompute@gmail.com** with your GPU model/count and CSV headers first. Do not send credentials, model weights or prompts.

A monthly ThermaCompute subscription is planned, not available through this tool. You may express interest at the same email without paying or committing to a subscription. CrashLens remains free.
