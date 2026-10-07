# ThermaCompute fleet assessment — experimental

The next validation target is one GPU fleet operator with a concrete thermal question. This offline prototype summarizes exported telemetry across GPUs; it is not a controller or a production-scale collector. CrashLens remains a separate log-triage tool.

## Run an invented two-GPU example

Python 3.10+, no dependencies, GPU, account or upload:

```sh
python fleet_assess.py examples/synthetic-fleet.csv --evidence-kind synthetic --out fleet-report.json
```

Open the JSON file locally. Expected: two GPUs, one with an explicitly reported thermal-throttle sample. All example data is invented. Existing output files are never overwritten.

## Input contract

Required CSV columns: `timestamp,gpu_id,temperature_c,power_w,thermal_throttle`.

- Timestamp: ISO 8601 with UTC offset; unique per GPU and instant.
- GPU ID: a stable alias unique across the assessed fleet (not a reused node-local index).
- Temperature in Celsius, power in watts: finite readings; power cannot be negative.
- Thermal throttle: explicit `0` or `1` from a documented thermal-specific signal. Do not infer it from temperature, general hardware slowdown, or nonzero generic throttle bitmasks. Decode source metrics separately and record that mapping.
- Additional columns are ignored. Missing or malformed required values reject the file. Input limit: 20 MiB.

This normalized CSV is not a direct parser for arbitrary DCGM exports. Confirm metric semantics before converting an export. Reports expose sample counts, extrema, time windows and interval ranges. They do not estimate throttle duration, energy, lost GPU-hours, root cause or savings. No flag does not prove absence of a problem. Different workloads and sampling patterns make naive GPU rankings misleading.

## First operator pilot

Seek an infrastructure engineer responsible for multiple GPUs who has a specific question about reported thermal throttling. Start with GPU model/count, the question, column headers, units, expected sampling cadence and available time window. Do not post private telemetry in GitHub issues. Keep the assessment local; review GPU identifiers before sharing any report. Files are not encrypted by this tool.

Success means the operator reviews a finding and identifies one recommendation worth testing, or names a missing check. Synthetic testing and sent invitations do not count as customer validation.

If suitable thermal telemetry exists, offer the separate [one-time $80 scoped audit](thermal-audit.md). Agree covered GPUs, observation window, deliverables, data handling and delivery date before payment. The free assessment is not the paid audit. Fleet-wide control and enterprise subscriptions remain future work.

## Progression toward control

Read-only evidence → operator-reviewed recommendation → supervised test group → bounded controller with tested local limits, stale-command rejection and rollback → gradual fleet rollout. This prototype implements only the first step. It has not been benchmarked at thousands or millions of GPUs and makes no autonomous changes.

## Evidence → recommendation → operator statement

Schema version 2 creates a recommendation only for a GPU with explicit thermal-throttle samples. Each record contains CSV record numbers (header is record 1), the observed window, an unverified hypothesis, alternative explanations, missing workload context, a read-only correlation test, approval status and an initially untested outcome. Source bytes receive a SHA-256 fingerprint. Fingerprints link records; they do not establish authenticity or prevent tampering.

Use `--evidence-kind synthetic` for invented input or `--evidence-kind operator_export` for an actual operator export. The default is `unspecified`; this is a user declaration, not automatic provenance verification. Even an operator export does not prove someone reviewed it.

To record a review, save a local JSON feedback object. The following is an **invented example, not customer feedback**:

```json
{
  "recommendation_id": "recommendation-1",
  "reviewer": "SYNTHETIC EXAMPLE — not a real operator",
  "decision": "needs_evidence",
  "useful_or_missing_check": "Need workload throughput aligned with the flagged samples."
}
```

```sh
python fleet_assess.py --review fleet-report.json --feedback feedback.json --out review-001.json
```

Allowed decisions: `accepted_for_investigation`, `rejected`, `needs_evidence`, `tested`. A tested statement additionally requires a `result` (improved/worsened/unchanged/inconclusive) and nonempty `test_description`, `measurements`, and `learning` strings. Include metric units, baseline and observed values in measurements. These are operator-entered narrative records, not calculated performance comparisons. Acceptance of an investigation never grants permission to change hardware.

Each review is a separate new file linked to the assessment fingerprint. The original assessment remains unchanged. Reports are local plaintext, not an authenticated or tamper-proof audit log; identity, authorization, measurement accuracy and causality are not independently verified. Review files are not ingested into training or shared between customers. No automatic model learning is implemented.

## Next validation gates

1. One real operator reviews a recommendation and names a useful or missing check. Record their actual response; a synthetic review does not satisfy this gate.
2. Agree the normalized metric mapping and obtain sufficient authorized, local workload context. Raw production logs are not needed for initial scoping.
3. Decide whether the question fits the $80 audit before offering or charging for it.
4. Only after meaningful evidence exists, specify an operator-run experiment with a comparable baseline, one changed variable, metric and success threshold, stop conditions and rollback. None of these controls is implemented as an execution engine here.
