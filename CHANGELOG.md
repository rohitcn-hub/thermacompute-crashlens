# Changelog

## 0.2.0 — 2026-09-29

- Adopt the Incident Lens reporting core under the CrashLens name.
- Preserve the one-file CLI; add multiple files and optional --out.
- Require Python 3.10+; replace the old overwritten Markdown file with a new output directory.
- Add JSON/HTML reports, source lines, best-effort redaction and conservative timestamp ordering.
- Separate generic hardware slowdown and GPU-lost messages from thermal/NVLink diagnoses.
- Remove unsupported root-cause, savings and report-length promises.
- Correct contact to vivaan.thermacompute@gmail.com.
- Add MIT license, synthetic demo, security guidance and regression tests.

Validation uses synthetic fixtures, not production fleet benchmarks.
