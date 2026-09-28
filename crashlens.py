import argparse
import re
import sys
import time
import os

class Colors:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

SIGNATURES = {
    "CUDA_OUT_OF_MEMORY": re.compile(r"CUDA out of memory|allocating.*bytes.*failed"),
    "NCCL_NETWORK_TIMEOUT": re.compile(r"Watchdog caught collective operation timeout|NCCL WARN"),
    "THERMAL_THROTTLE_DETECTED": re.compile(r"HW Slowdown|Thermal Throttling|temperature exceeds"),
    "NVLINK_FAILURE": re.compile(r"NVLink.*error|GPU is lost"),
    "WORKER_CRASH": re.compile(r"Worker \(pid:\d+\) exited unexpectedly|Segmentation fault"),
}

def analyze_log(file_path):
    print(f"\n{Colors.CYAN}{Colors.BOLD}===================================================={Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}   ThermaCompute CrashLens - Log Triage Engine      {Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}===================================================={Colors.ENDC}")
    
    findings = {key: [] for key in SIGNATURES.keys()}
    line_count = 0
    start_time = time.time()

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                line_count += 1
                for sig_name, pattern in SIGNATURES.items():
                    if pattern.search(line):
                        findings[sig_name].append((i, line.strip()))
    except FileNotFoundError:
        print(f"{Colors.FAIL}[ERROR] Log file not found: {file_path}{Colors.ENDC}")
        sys.exit(1)

    elapsed = time.time() - start_time
    total_findings = sum(len(v) for v in findings.values())

    if total_findings == 0:
        print(f"{Colors.GREEN}[+] Scan Complete. No critical signatures found.{Colors.ENDC}\n")
        return

    # Terminal Output
    print(f"{Colors.FAIL}{Colors.BOLD}[!] CRITICAL FAILURES ISOLATED{Colors.ENDC}")
    for sig, occurrences in findings.items():
        if occurrences:
            print(f"{Colors.WARNING}>> {sig} (Detected {len(occurrences)} times){Colors.ENDC}")
            print(f"   Line {occurrences[0][0]}: {Colors.FAIL}{occurrences[0][1][:120]}...{Colors.ENDC}\n")

    # Generate Markdown Artifact
    report_path = "crash_report.md"
    with open(report_path, "w") as md:
        md.write(f"# ThermaCompute CrashLens Report\n")
        md.write(f"**Target:** `{os.path.basename(file_path)}` | **Lines Scanned:** `{line_count}`\n\n")
        md.write("## Isolated Failures\n")
        for sig, occurrences in findings.items():
            if occurrences:
                md.write(f"- **{sig}** (x{len(occurrences)})\n")
                md.write(f"  - *First instance (Line {occurrences[0][0]}):* `{occurrences[0][1][:150]}`\n")
    
    print(f"{Colors.GREEN}[+] Generated shareable team report: {report_path}{Colors.ENDC}")

    # Contextual Upsell - ONLY triggers if heat issues are found
    if findings["THERMAL_THROTTLE_DETECTED"]:
        print(f"\n{Colors.HEADER}{Colors.BOLD}*** THERMAL THROTTLING DETECTED ***{Colors.ENDC}")
        print("CrashLens noticed your GPUs are dropping clocks due to heat.")
        print("This is costing you compute capacity and increasing latency.")
        print("Book our $80 GPU Efficiency Audit to get a 30-page forensic teardown.")
        print(f"{Colors.GREEN}Email: vivann.thermacompute@gmail.com{Colors.ENDC}")
        print(f"{Colors.CYAN}===================================================={Colors.ENDC}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ThermaCompute CrashLens - Fast Inference Log Triage")
    parser.add_argument("log_file", help="Path to the server log file")
    args = parser.parse_args()
    analyze_log(args.log_file)
