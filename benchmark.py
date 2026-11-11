import concurrent.futures
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request


RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
FLASK_URL = "http://localhost:5000/"
PAYLOAD = {"sender": "bench_user", "message": "Hello"}

CONCURRENCY_LEVELS = [1, 10, 25, 50]
REQUESTS_PER_LEVEL = 100
WARMUP_REQUESTS = 5


def get_codespace_specs():
    vcpus = os.cpu_count() or 2
    ram_gb = "Unknown"
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    ram_gb = f"{int(line.split()[1]) / (1024 * 1024):.1f} GB"
                    break
    return f"{vcpus} vCPUs, {ram_gb} RAM ({platform.system()} {platform.release()})"


def get_docker_stats():
    try:
        cmd = [
            "docker", "stats", "--no-stream",
            "--format", "{{.Name}}: {{.MemUsage}} (CPU {{.CPUPerc}})"
        ]
        out = subprocess.check_output(cmd, text=True).strip().splitlines()
        return " ; ".join(out) if out else "N/A"
    except Exception:
        return "N/A"


def send_request(target_url, is_post, req_id):
    if is_post:
        body = json.dumps({**PAYLOAD, "sender": f"user_{req_id}"}).encode("utf-8")
        req = urllib.request.Request(
            target_url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
    else:
        req = urllib.request.Request(target_url, method="GET")

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
            return (time.perf_counter() - start) * 1000.0, resp.status == 200
    except Exception:
        return (time.perf_counter() - start) * 1000.0, False


def run_tier(target_url, is_post, concurrency):
    latencies = []
    t0 = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(send_request, target_url, is_post, i)
            for i in range(REQUESTS_PER_LEVEL)
        ]
        for f in concurrent.futures.as_completed(futures):
            ms, _ = f.result()
            latencies.append(ms)

    elapsed = time.perf_counter() - t0
    latencies.sort()
    n = len(latencies)
    return (
        REQUESTS_PER_LEVEL / elapsed,
        latencies[int(n * 0.50)],
        latencies[int(n * 0.95)],
        latencies[min(int(n * 0.99), n - 1)],
    )


if __name__ == "__main__":
    # 1. Check if Rasa REST webhook on port 5005 is ready
    _, rasa_ok = send_request(RASA_URL, True, "healthcheck")
    if rasa_ok:
        active_url, is_post, label = RASA_URL, True, "Rasa NLU Inference Container (Port 5005)"
    else:
        _, flask_ok = send_request(FLASK_URL, False, "healthcheck")
        if flask_ok:
            active_url, is_post, label = FLASK_URL, False, "Flask Web Service Container (Port 5000)"
        else:
            print("ERROR: Neither port 5005 (Rasa) nor port 5000 (Flask) responded.")
            print("Run 'docker compose up -d' and wait 30 seconds for Rasa to load its model.")
            sys.exit(1)

    for i in range(WARMUP_REQUESTS):
        send_request(active_url, is_post, f"warmup_{i}")

    print("## System Performance & Tail-Latency Benchmark\n")
    print(f"- **Cloud Testbed:** GitHub Codespaces ({get_codespace_specs()})")
    print(f"- **Target Service:** {label}")
    print(f"- **Workload:** {REQUESTS_PER_LEVEL} requests per concurrency tier ({WARMUP_REQUESTS} warm-up requests)\n")
    print("| Concurrency | Throughput | p50 Latency | p95 Latency | p99 Latency |")
    print("|---|---|---|---|---|")

    for c in CONCURRENCY_LEVELS:
        rps, p50, p95, p99 = run_tier(active_url, is_post, c)
        print(f"| {c} workers | {rps:.2f} req/s | {p50:.1f} ms | {p95:.1f} ms | {p99:.1f} ms |")

    print(f"\n- **Peak Container Footprint:** {get_docker_stats()}")