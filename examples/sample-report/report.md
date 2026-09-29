# ThermaCompute CrashLens

Version 0.2.0 — local heuristic triage

Status: matches_found
Lines scanned: 5
Ordering: UTC timestamp order (clock synchronization unverified)

## Limitations
- Heuristic signature matches, not confirmed root causes or a health certificate.
- Redaction is best effort. Review all output before sharing; paths, hostnames and other secrets may remain.
- No-event results do not mean a healthy system. Only listed signatures are recognized.
- Clock synchronization and log completeness cannot be verified from these files.

## Signature counts (not unique incident counts)
- gpu_oom: 1
- worker_exit: 1
- nccl_timeout: 1

## GPU allocation failure reported
Source: input-1:3 | 2026-09-28T10:00:04+00:00

Evidence:

    2026-09-28T10:00:04Z worker=0 torch.cuda.OutOfMemoryError: CUDA out of memory. Tried to allocate 512 MiB

Next check: Inspect memory usage and allocation context on the affected worker; distinguish model loading, cache allocation and CUDA graph capture. Do not assume that reducing one flag fixes all OOMs.

## Worker or engine failure reported
Source: input-1:4 | 2026-09-28T10:00:05+00:00

Evidence:

    2026-09-28T10:00:05Z worker=0 Worker failed with error

Next check: Find the underlying exception in this worker and its peers. This message may be a consequence rather than the initial error.

## Collective timeout reported
Source: input-1:5 | 2026-09-28T10:02:00+00:00

Evidence:

    2026-09-28T10:02:00Z worker=1 Watchdog caught collective operation timeout

Next check: Inspect other ranks for earlier failures. The rank reporting a timeout is not necessarily the culprit. Consider existing PyTorch Flight Recorder evidence.
