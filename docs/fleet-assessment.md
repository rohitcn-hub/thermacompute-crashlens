# ThermaCompute fleet assessment — experimental

The next validation target is one GPU fleet operator with a concrete thermal question. This offline prototype summarizes exported telemetry across GPUs; it is not a controller or a production-scale collector. CrashLens remains a separate log-triage tool.

## Run an invented two-GPU example

Python 3.10+, no dependencies, GPU, account or upload:

```sh
python fleet_assess.py examples/synthetic-fleet.csv --out fleet-report.json
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
