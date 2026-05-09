"""
bench_providers.py — Benchmark LLM providers cho N5 activity generation.

Mục đích:
  So sánh latency / quality giữa Gemini và Groq trên tập fixture cố định,
  xuất CSV + markdown table để đưa vào báo cáo.

Cách chạy:
  python tests/bench_providers.py
  python tests/bench_providers.py --providers gemini --runs 1
  python tests/bench_providers.py --no-parallel

Output:
  tests/bench_results/bench_<timestamp>.csv       — raw data, 1 row = 1 run
  tests/bench_results/bench_<timestamp>.md        — tổng hợp per-provider

Lưu ý:
  - Cache N5 bị clear giữa mỗi run để đo cold latency thực sự.
  - Parallel mode cap ở MAX_CONCURRENCY=3 (giống frontend). Nếu gặp 429
    nhiều, dùng --no-parallel để chạy tuần tự.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────
_here    = Path(__file__).resolve().parent
_root    = _here.parent
_backend = _root / "backend"
for p in (str(_root), str(_backend)):     # root cho `config`, backend cho `modules`
    if p not in sys.path:
        sys.path.insert(0, p)

from modules.n5_activity_generation.n5_llm_generator import generate_from_llm_with_meta
from modules.n5_activity_generation import cache as llm_cache


# =============================================================================
# FIXTURES
# =============================================================================

LOCATIONS = [
    {
        "name": "Ha Long",
        "description": "Vịnh biển với hàng nghìn đảo đá vôi, di sản UNESCO",
        "tags": ["beach", "island", "scenic"],
    },
    {
        "name": "Sa Pa",
        "description": "Thị trấn vùng cao Tây Bắc với ruộng bậc thang và văn hóa dân tộc",
        "tags": ["mountain", "trekking", "ethnic"],
    },
    {
        "name": "Hoi An",
        "description": "Phố cổ với kiến trúc truyền thống, ẩm thực nổi tiếng",
        "tags": ["heritage", "food", "culture"],
    },
    {
        "name": "Da Lat",
        "description": "Thành phố ngàn hoa với khí hậu mát mẻ quanh năm",
        "tags": ["flower", "romantic", "scenic"],
    },
    {
        "name": "Phu Quoc",
        "description": "Đảo ngọc phía nam với bãi biển và hải sản",
        "tags": ["beach", "island", "seafood"],
    },
]

USER_PROFILES = [
    {
        "name": "adventure",
        "text": "Tôi muốn trải nghiệm mạo hiểm và chụp ảnh đẹp",
        "tags": ["adventure", "photography", "trekking"],
    },
    {
        "name": "relax",
        "text": "Chuyến đi thư giãn, tận hưởng thiên nhiên yên bình",
        "tags": ["relax", "spa", "scenic"],
    },
    {
        "name": "food",
        "text": "Khám phá ẩm thực và văn hóa địa phương",
        "tags": ["food", "local_food", "culture"],
    },
]

MAX_CONCURRENCY = 3


# =============================================================================
# SINGLE BENCHMARK RUN
# =============================================================================

def run_one(provider: str, location: dict, profile: dict, run_idx: int) -> dict:
    """
    Chạy 1 lần generate_from_llm_with_meta + đo:
      - latency_ms       (wall-clock toàn bộ, gồm retry)
      - success          (có trả activities không)
      - num_activities
      - avg_tags         (tags trung bình/activity)
      - avg_desc_length  (độ dài description trung bình)
      - provider_used    (provider thực sự đã trả response — có thể khác nếu fallback)
      - error            (string mô tả lỗi nếu có)
    """
    # Cache clear để đo cold latency cho từng run
    llm_cache.clear()

    t0 = time.time()
    try:
        activities, meta = generate_from_llm_with_meta(
            location_name=location["name"],
            location_description=location["description"],
            location_tags=location["tags"],
            user_tags=profile["tags"],
            budget_per_activity=500_000,
            max_time_per_activity=240,
            num_activities=10,
            schema_v2=True,
            user_text=profile["text"],
            provider=provider,
        )
        wall_ms = int((time.time() - t0) * 1000)
        error = ""
    except Exception as e:
        wall_ms = int((time.time() - t0) * 1000)
        activities, meta, error = None, {}, f"{type(e).__name__}: {e}"

    success = bool(activities)
    num = len(activities) if activities else 0
    avg_tags = (
        statistics.mean(len(a.get("tags", [])) for a in activities) if success else 0
    )
    avg_desc = (
        statistics.mean(len(a.get("description", "") or "") for a in activities) if success else 0
    )

    return {
        "provider":       provider,
        "location":       location["name"],
        "profile":        profile["name"],
        "run_idx":        run_idx,
        "success":        int(success),
        "latency_ms":     wall_ms,
        "num_activities": num,
        "avg_tags":       round(avg_tags, 2),
        "avg_desc_len":   round(avg_desc, 1),
        "provider_used":  meta.get("provider_used", ""),
        "error":          error,
    }


# =============================================================================
# CLI / ORCHESTRATOR
# =============================================================================

def run_all(providers, runs: int, parallel: bool) -> list:
    """Sinh toàn bộ combinations + chạy (parallel hoặc tuần tự)."""
    combos = [
        (p, loc, prof, r)
        for p in providers
        for loc in LOCATIONS
        for prof in USER_PROFILES
        for r in range(1, runs + 1)
    ]
    total = len(combos)
    results = []

    print(f"Running {total} benchmark iterations "
          f"(providers={providers}, locations={len(LOCATIONS)}, "
          f"profiles={len(USER_PROFILES)}, runs={runs}, "
          f"mode={'parallel' if parallel else 'sequential'})")

    if parallel:
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
            futs = {pool.submit(run_one, *c): c for c in combos}
            done = 0
            for fut in as_completed(futs):
                row = fut.result()
                done += 1
                print(f"[{done}/{total}] {row['provider']:>6} | {row['location']:>10} | "
                      f"{row['profile']:>10} | run {row['run_idx']} | "
                      f"ok={row['success']} {row['latency_ms']}ms "
                      f"n={row['num_activities']}")
                results.append(row)
    else:
        for i, combo in enumerate(combos, 1):
            row = run_one(*combo)
            print(f"[{i}/{total}] {row['provider']:>6} | {row['location']:>10} | "
                  f"{row['profile']:>10} | run {row['run_idx']} | "
                  f"ok={row['success']} {row['latency_ms']}ms "
                  f"n={row['num_activities']}")
            results.append(row)

    return results


def write_csv(results: list, path: Path) -> None:
    if not results:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)


def summarize(results: list) -> dict:
    """Tổng hợp per-provider: success rate, latency p50/p95/avg, quality."""
    by_provider = {}
    for row in results:
        by_provider.setdefault(row["provider"], []).append(row)

    summary = {}
    for name, rows in by_provider.items():
        total = len(rows)
        ok_rows = [r for r in rows if r["success"]]
        ok = len(ok_rows)
        latencies_ok = [r["latency_ms"] for r in ok_rows]
        summary[name] = {
            "runs":          total,
            "success":       ok,
            "success_rate":  round(ok / total, 3) if total else 0,
            "latency_avg":   int(statistics.mean(latencies_ok)) if latencies_ok else 0,
            "latency_p50":   int(statistics.median(latencies_ok)) if latencies_ok else 0,
            "latency_p95":   int(_percentile(latencies_ok, 0.95)) if latencies_ok else 0,
            "avg_tags":      round(statistics.mean(r["avg_tags"] for r in ok_rows), 2) if ok_rows else 0,
            "avg_desc_len":  round(statistics.mean(r["avg_desc_len"] for r in ok_rows), 1) if ok_rows else 0,
            "num_avg":       round(statistics.mean(r["num_activities"] for r in ok_rows), 1) if ok_rows else 0,
        }
    return summary


def _percentile(values, p):
    """Percentile đơn giản (linear interpolation)."""
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def write_markdown(results: list, summary: dict, path: Path, args) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# LLM Provider Benchmark — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Providers: {', '.join(args.providers)}",
        f"- Locations: {len(LOCATIONS)} ({', '.join(l['name'] for l in LOCATIONS)})",
        f"- Profiles: {len(USER_PROFILES)} ({', '.join(p['name'] for p in USER_PROFILES)})",
        f"- Runs per combo: {args.runs}",
        f"- Mode: {'parallel' if not args.no_parallel else 'sequential'} "
        f"(max_workers={MAX_CONCURRENCY})",
        f"- Total iterations: {len(results)}",
        "",
        "## Summary per provider",
        "",
        "| Provider | Runs | Success | Rate | Latency avg | p50 | p95 | Activities/run | Avg tags | Avg desc |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, s in summary.items():
        lines.append(
            f"| {name} | {s['runs']} | {s['success']} | {s['success_rate']:.0%} | "
            f"{s['latency_avg']}ms | {s['latency_p50']}ms | {s['latency_p95']}ms | "
            f"{s['num_avg']} | {s['avg_tags']} | {s['avg_desc_len']} |"
        )

    lines += ["", "## Raw results", "",
              "| Provider | Location | Profile | Run | OK | Latency | N | Tags | Desc | Used | Error |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| {r['provider']} | {r['location']} | {r['profile']} | {r['run_idx']} | "
            f"{r['success']} | {r['latency_ms']}ms | {r['num_activities']} | "
            f"{r['avg_tags']} | {r['avg_desc_len']} | {r['provider_used']} | "
            f"{r['error'][:60]} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--providers", default="gemini,groq",
        help="CSV list of providers to benchmark (default: gemini,groq)",
    )
    parser.add_argument(
        "--runs", type=int, default=2,
        help="Số lần lặp mỗi (provider, location, profile). Default 2.",
    )
    parser.add_argument(
        "--no-parallel", action="store_true",
        help="Chạy tuần tự thay vì ThreadPool(3). Dùng khi hay bị 429.",
    )
    parser.add_argument(
        "--output-dir", default=str(_here / "bench_results"),
        help="Thư mục xuất CSV + MD.",
    )
    args = parser.parse_args()
    args.providers = [p.strip() for p in args.providers.split(",") if p.strip()]

    results = run_all(args.providers, args.runs, parallel=not args.no_parallel)
    summary = summarize(results)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.output_dir)
    csv_path = out / f"bench_{ts}.csv"
    md_path  = out / f"bench_{ts}.md"

    write_csv(results, csv_path)
    write_markdown(results, summary, md_path, args)

    print("")
    print(f"Results: {csv_path}")
    print(f"Summary: {md_path}")
    print("")
    for name, s in summary.items():
        print(f"  {name}: {s['success']}/{s['runs']} ok "
              f"({s['success_rate']:.0%}), avg {s['latency_avg']}ms, "
              f"p95 {s['latency_p95']}ms")


if __name__ == "__main__":
    main()
