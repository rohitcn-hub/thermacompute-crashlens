import argparse
import re
import sys
import time

# ANSI Terminal Colors for an enterprise feel
class Colors:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# The core failure signatures for AI infrastructure
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
    print(f"Scanning target: {file_path}...\n")
    
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
        print(f"{Colors.GREEN}[+] Scan Complete.{Colors.ENDC} Analyzed {line_count} lines in {elapsed:.4f}s.")
        print(f"{Colors.GREEN}[+] No critical hardware or framework signatures found.{Colors.ENDC}\n")
        return

    print(f"{Colors.FAIL}{Colors.BOLD}[!] CRITICAL FAILURES ISOLATED{Colors.ENDC}")
    print(f"Analyzed {line_count} lines in {elapsed:.4f}s.\n")

    for sig, occurrences in findings.items():
        if occurrences:
            print(f"{Colors.WARNING}>> {sig} (Detected {len(occurrences)} times){Colors.ENDC}")
            print(f"   First instance at Line {occurrences[0][0]}:")
            print(f"   {Colors.FAIL}{occurrences[0][1][:150]}...{Colors.ENDC}\n")
            
    print(f"{Colors.CYAN}===================================================={Colors.ENDC}")
    print(f"{Colors.BOLD}NEXT STEPS & RESOLUTION:{Colors.ENDC}")
    
    if findings["CUDA_OUT_OF_MEMORY"]:
        print(" - OOM: Reduce vLLM batch size, lower MAX_MODEL_LEN, or check KV Cache allocation.")
    if findings["NCCL_NETWORK_TIMEOUT"] or findings["NVLINK_FAILURE"]:
        print(" - NETWORK/BUS: Verify node-to-node connectivity and NVLink health. A trailing worker is stalling the ring.")
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}*** UPGRADE TO THE FULL $80 THERMAL AUDIT ***{Colors.ENDC}")
    print("CrashLens tells you why the server died.")
    print("The ThermaCompute $80 Audit tells you why your cluster is bleeding 20% of its capacity to heat.")
    print("Zero production access required. We analyze your DCGM logs offline.")
    print(f"{Colors.GREEN}Email: vivann.thermacompute@gmail.com to book your audit.{Colors.ENDC}")
    print(f"{Colors.CYAN}===================================================={Colors.ENDC}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ThermaCompute CrashLens - Fast Inference Log Triage")
    parser.add_argument("log_file", help="Path to the server log file (.txt or .log)")
    args = parser.parse_args()
    
    analyze_log(args.log_file)
