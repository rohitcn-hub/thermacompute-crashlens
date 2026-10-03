# CrashLens: a five-minute local trial

This is a synthetic demonstration, not a customer incident or production validation.

## Run it

Python 3.10+ is required. No GPU, account or API key is needed.

```sh
git clone https://github.com/rohitcn-hub/thermacompute-crashlens.git
cd thermacompute-crashlens
python crashlens.py examples/synthetic.log --out demo-report
```

Open `demo-report/report.html`. Choose a new output folder if it already exists.

## What the included fixture shows

| Time (UTC) | Saved log evidence | Matched signature | Suggested investigation |
| --- | --- | --- | --- |
| 10:00:04 | CUDA out of memory; allocation of 512 MiB attempted | GPU allocation failure | Inspect affected worker memory and allocation context. |
| 10:00:05 | Worker failed with error | Worker failure | Find the underlying exception in this worker and peers. |
| 10:02:00 | Watchdog caught collective operation timeout | Collective timeout | Inspect earlier failures on other ranks; the timeout rank need not be the culprit. |

Verified on October 3, 2026 with the current repository script: `matches_found: 3 matches` and local HTML, Markdown and JSON reports.

The ordering helps focus investigation. It does not prove that the allocation failure caused the timeout, and contains no evidence establishing a thermal cause. Clock synchronization and log completeness are unverified. Signature counts are not unique incident counts.

## Give one useful critique

Did the report give you a useful next check? What was missing or misleading?

Comment on [the feedback issue](https://github.com/rohitcn-hub/thermacompute-crashlens/issues/2) or email vivaan.thermacompute@gmail.com. Include your OS, Python version and the step that failed if you need onboarding help. Do not post production logs or secrets. Masking is incomplete; review outputs before sharing.

## When the $80 thermal audit fits

CrashLens stays free. If you need a deeper thermal review, email your GPU model/count and telemetry CSV headers first. We confirm suitable data and scope before payment. The separate $80 audit reviews agreed temperature, power and reported throttling, providing supported findings, prioritized checks and a PDF with assumptions. It does not establish all system flaws, promise savings or make production changes. Optional further service is discussed separately.
