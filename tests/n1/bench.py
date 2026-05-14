"""
N1 Embedding — Module Bench Test
Runs all test cases, measures latency, validates vector properties,
and outputs bench_n1_results.json.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.modules.n1_embedding import embed, embed_batch
from config import EMBEDDING_MODEL_NAME

BASE_DIR = Path(__file__).resolve().parent

# ── Re-use test cases from test.py ────────────────────────────────────────────
from test import USER_TESTS, LOCATION_TESTS

CHANNELS = ["text", "aug_text", "aug_tags", "img_desc"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(v: list[float] | None) -> float | None:
    if v is None:
        return None
    return round(math.sqrt(sum(x * x for x in v)), 6)


def _dim(v: list[float] | None) -> int | None:
    return len(v) if v is not None else None


def _analyse_result(result: dict) -> dict:
    vecs = result.get("vectors", {})
    return {
        "text_k": result.get("text_k"),
        "tags_k": result.get("tags_k"),
        "preprocessed": result.get("preprocessed", {}),
        "vector_dims": {ch: _dim(vecs.get(ch)) for ch in CHANNELS},
        "vector_norms": {ch: _norm(vecs.get(ch)) for ch in CHANNELS},
        "channels_present": [ch for ch in CHANNELS if vecs.get(ch) is not None],
        "channels_null": [ch for ch in CHANNELS if vecs.get(ch) is None],
    }


def _vectors_close(a: list[float] | None, b: list[float] | None, tol: float = 1e-5) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= tol for x, y in zip(a, b))

# ── Single tests ──────────────────────────────────────────────────────────────

def run_single_tests(test_set: list[dict], label: str) -> tuple[list[dict], float]:
    records = []
    for t in test_set:
        inp = {"text": t["text"], "tags": t["tags"], "img_desc": t["img_desc"]}
        t0 = time.perf_counter()
        result = embed(inp)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        records.append({
            "name": t["name"],
            "input": inp,
            "analysis": _analyse_result(result),
            "latency_ms": round(elapsed_ms, 2),
        })
        print(f"  [{label}] {t['name']} — {elapsed_ms:.1f}ms  text_k={result['text_k']} tags_k={result['tags_k']}")

    avg = sum(r["latency_ms"] for r in records) / len(records) if records else 0
    return records, round(avg, 2)


# ── Batch tests ───────────────────────────────────────────────────────────────

def run_batch_test(test_set: list[dict], label: str) -> dict:
    inputs = [{"text": t["text"], "tags": t["tags"], "img_desc": t["img_desc"]} for t in test_set]
    t0 = time.perf_counter()
    results = embed_batch(inputs)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    items = []
    for t, res in zip(test_set, results):
        items.append({
            "name": t["name"],
            "analysis": _analyse_result(res),
        })

    print(f"  [{label} batch] {len(inputs)} items — {elapsed_ms:.1f}ms total  ({elapsed_ms/len(inputs):.1f}ms/item)")
    return {
        "label": label,
        "n_items": len(inputs),
        "latency_ms": round(elapsed_ms, 2),
        "latency_per_item_ms": round(elapsed_ms / len(inputs), 2),
        "items": items,
    }


# ── Consistency check: single vs batch ────────────────────────────────────────

def check_batch_consistency(test_set: list[dict], label: str) -> dict:
    """Verify each batch result matches its individual embed() call."""
    inputs = [{"text": t["text"], "tags": t["tags"], "img_desc": t["img_desc"]} for t in test_set]
    batch_results = embed_batch(inputs)
    mismatches = []
    for t, batch_res in zip(test_set, batch_results):
        single_res = embed({"text": t["text"], "tags": t["tags"], "img_desc": t["img_desc"]})
        for ch in CHANNELS:
            bv = (batch_res.get("vectors") or {}).get(ch)
            sv = (single_res.get("vectors") or {}).get(ch)
            if not _vectors_close(bv, sv):
                mismatches.append({"name": t["name"], "channel": ch})

    consistent = len(mismatches) == 0
    print(f"  [{label} consistency] {'PASS' if consistent else 'FAIL'} — {len(mismatches)} mismatch(es)")
    return {"consistent": consistent, "mismatches": mismatches}


# ── Norm check ────────────────────────────────────────────────────────────────

def check_norms(single_records: list[dict]) -> dict:
    """Verify all non-null vectors have norm ≈ 1.0 (normalized embeddings)."""
    failures = []
    for rec in single_records:
        for ch, norm in rec["analysis"]["vector_norms"].items():
            if norm is None:
                continue
            if abs(norm - 1.0) > 1e-3:
                failures.append({"name": rec["name"], "channel": ch, "norm": norm})
    return {"all_normalized": len(failures) == 0, "failures": failures}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    output = {
        "metadata": {
            "module": "N1 — Embedding",
            "model": EMBEDDING_MODEL_NAME,
            "vector_dim": 1024,
            "channels": CHANNELS,
            "date": "2026-05-13",
        },
        "single_tests": {},
        "batch_tests": {},
        "checks": {},
        "summary": {},
    }

    print("\n=== N1 BENCH: Single tests ===")
    user_records, user_avg = run_single_tests(USER_TESTS, "user")
    loc_records, loc_avg = run_single_tests(LOCATION_TESTS, "location")
    all_single = user_records + loc_records

    output["single_tests"] = {
        "user": {"records": user_records, "avg_latency_ms": user_avg},
        "location": {"records": loc_records, "avg_latency_ms": loc_avg},
    }

    print("\n=== N1 BENCH: Batch tests ===")
    output["batch_tests"]["user"] = run_batch_test(USER_TESTS, "user")
    output["batch_tests"]["location"] = run_batch_test(LOCATION_TESTS, "location")

    print("\n=== N1 BENCH: Consistency checks ===")
    output["checks"]["batch_vs_single_user"] = check_batch_consistency(USER_TESTS, "user")
    output["checks"]["batch_vs_single_location"] = check_batch_consistency(LOCATION_TESTS, "location")

    print("\n=== N1 BENCH: Norm checks ===")
    norm_result = check_norms(all_single)
    output["checks"]["norm_validation"] = norm_result
    print(f"  Norm validation: {'PASS' if norm_result['all_normalized'] else 'FAIL'}")

    # ── Summary ──────────────────────────────────────────────────────
    all_latencies = [r["latency_ms"] for r in all_single]
    text_k_vals = [r["analysis"]["text_k"] for r in all_single]
    tags_k_vals = [r["analysis"]["tags_k"] for r in all_single]

    # Null channel stats
    null_img_desc_count = sum(
        1 for r in all_single if "img_desc" in r["analysis"]["channels_null"]
    )

    output["summary"] = {
        "total_single_tests": len(all_single),
        "user_avg_latency_ms": user_avg,
        "location_avg_latency_ms": loc_avg,
        "overall_avg_latency_ms": round(sum(all_latencies) / len(all_latencies), 2),
        "batch_user_latency_ms": output["batch_tests"]["user"]["latency_ms"],
        "batch_location_latency_ms": output["batch_tests"]["location"]["latency_ms"],
        "text_k_range": [min(text_k_vals), max(text_k_vals)],
        "tags_k_range": [min(tags_k_vals), max(tags_k_vals)],
        "tests_with_null_img_desc": null_img_desc_count,
        "all_norms_correct": norm_result["all_normalized"],
        "batch_consistent": (
            output["checks"]["batch_vs_single_user"]["consistent"]
            and output["checks"]["batch_vs_single_location"]["consistent"]
        ),
    }

    out_path = BASE_DIR / "bench_n1_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {out_path}")

    print("\n=== SUMMARY ===")
    s = output["summary"]
    print(f"  Single avg latency:  user={s['user_avg_latency_ms']}ms  loc={s['location_avg_latency_ms']}ms")
    print(f"  Batch latency:       user={s['batch_user_latency_ms']}ms  loc={s['batch_location_latency_ms']}ms")
    print(f"  text_k range: {s['text_k_range']}   tags_k range: {s['tags_k_range']}")
    print(f"  Null img_desc vectors: {s['tests_with_null_img_desc']}/{s['total_single_tests']}")
    print(f"  All norms ~1.0:  {s['all_norms_correct']}")
    print(f"  Batch == Single:    {s['batch_consistent']}")


if __name__ == "__main__":
    main()
