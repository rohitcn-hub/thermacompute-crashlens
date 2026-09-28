# 🛑 ThermaCompute CrashLens

**Inference jobs fail. The useful error usually gets buried under 10,000 lines of meaningless traceback.**

CrashLens is a fast, local, zero-dependency log parser engineered for SREs and inference teams running vLLM, PyTorch, and DeepSpeed. It scans massive server logs to isolate the exact cause of a crash and tells you exactly what to check next.

### Why use this?
- **Zero Production Access:** Runs locally on your machine. You never pipe sensitive logs to a cloud API.
- **Blazing Fast:** Parses thousands of lines in milliseconds.
- **Targeted:** Built specifically for modern AI stacks (CUDA OOM, NCCL Timeouts, Thermal Throttling, NVLink errors).

---

## ⚡ The Setup
No bloated installs. Just download and run. Requires Python 3.6+.

```bash
python crashlens.py path/to/your/server_crash.log
