#!/usr/bin/env python3
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

def fetch(url:str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.getcode()
    except Exception as e:
        return -1

def concurrent_get(url, n=10):
    t0 = time.perf_counter()
    codes = []
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = [ex.submit(fetch, url) for _ in range(n)]
        for f in as_completed(futs):
            codes.append(f.result())
    dt = time.perf_counter() - t0
    return dt, codes

def throughput_test(url, rps, seconds=3):
    t_end = time.perf_counter() + seconds
    sent = 0
    ok = 0
    while time.perf_counter() < t_end:
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=rps) as ex:
            futs = [ex.submit(fetch, url) for _ in range(rps)]
            for f in as_completed(futs):
                code = f.result()
                if code == 200:
                    ok += 1
                sent += 1
        elapsed = time.perf_counter() - t0
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
    return sent, ok, ok/seconds

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8083/")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--rps_spammer", type=int, default=20)
    ap.add_argument("--rps_normal", type=int, default=4)
    ap.add_argument("--seconds", type=int, default=5)
    args = ap.parse_args()

    print(f"[Benchmark] {args.n} concurrent requests to {args.url}")
    dt, codes = concurrent_get(args.url, args.n)
    print(f"Elapsed: {dt:.3f}s, codes: {codes}")

    print(f"\n[Throughput] Spammer (~{args.rps_spammer} rps) for {args.seconds}s")
    sent, ok, tps = throughput_test(args.url, args.rps_spammer, args.seconds)
    print(f"Sent={sent}, OK={ok}, OK/sec≈{tps:.2f}")

    print(f"\n[Throughput] Near-limit user (~{args.rps_normal} rps) for {args.seconds}s")
    sent, ok, tps = throughput_test(args.url, args_rps_normal := args.rps_normal, args.seconds)
    print(f"Sent={sent}, OK={ok}, OK/sec≈{tps:.2f}")
