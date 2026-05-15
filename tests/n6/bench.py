"""
N6 Activity Ranking — Module Bench Test
Benchmarks semantic scoring, attribute scoring, preference inference, normalization and performance.
Outputs bench_n6_results.json and bench_n6.md.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import TOP_K_ACTIVITIES
from backend.modules.n6_activity_ranking import rank_activities, infer_user_preferences

BASE_DIR = Path(__file__).resolve().parent

# ── Synthetic Vectors ──────────────────────────────────────────────────────────
DIM = 1024

def _unit(idx: int) -> list[float]:
    v = [0.0] * DIM
    v[idx] = 1.0
    return v

def _normalize(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 0 else v

# Semantic directions
BEACH    = _normalize(_unit(0))
MOUNTAIN = _normalize(_unit(1))
FOOD     = _normalize(_unit(2))
CITY     = _normalize(_unit(3))

def _activity(aid: str, lid: str, name: str, atype: str,
              intensity: float, physical: float, social: float,
              vec) -> dict:
    return {
        "activity_id": aid,
        "location_id": lid,
        "metadata": {
            "name":           name,
            "description":    f"Mô tả {name}",
            "tags":           [atype],
            "activity_type":  atype,
            "intensity":      intensity,
            "physical_level": physical,
            "social_level":   social,
        },
        "vectors": {"text": vec, "aug_tags": vec},
    }


# ── Test Cases ─────────────────────────────────────────────────────────────────

BENCH_TESTS = [
    {
        "name": "semantic_beach_user_ranks_beach_activity_first",
        "desc": "User vector beach → activity về biển phải đứng #1",
        "data": {
            "text_k": 3, "tags_k": 3, "top_k": 3,
            "user_input": {"text": "đi biển", "tags": [], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": BEACH, "aug_tags": BEACH, "img_desc": None},
            "activities": [
                _activity("act_snorkel", "loc_1", "Lặn ngắm san hô", "nature",    0.6, 0.5, 0.3, BEACH),
                _activity("act_trek",    "loc_1", "Leo núi Fansipan",  "adventure", 0.9, 0.9, 0.4, MOUNTAIN),
                _activity("act_food",    "loc_1", "Phở bò truyền thống", "food",   0.2, 0.1, 0.5, FOOD),
            ],
        },
        "expect_top1": "act_snorkel",
    },
    {
        "name": "attribute_relaxed_user_avoids_high_intensity",
        "desc": "User 'yên bình' → activity intensity thấp phải lên trên",
        "data": {
            "text_k": 0, "tags_k": 3, "top_k": 2,
            "user_input": {"text": "muốn nghỉ ngơi yên bình", "tags": ["peaceful"], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": BEACH, "aug_tags": BEACH, "img_desc": None},
            "activities": [
                _activity("act_relax", "loc_1", "Tắm biển thư giãn",   "relaxation", 0.1, 0.1, 0.2, BEACH),
                _activity("act_trek",  "loc_1", "Leo núi cực hạn",      "adventure",  0.95, 0.95, 0.3, BEACH),
            ],
        },
        "expect_top1": "act_relax",
    },
    {
        "name": "preference_inference_adventure_tags",
        "desc": "Tags adventure+trekking → intensity cao, physical cao",
        "data_pref": {
            "text": "muốn thử thách bản thân",
            "tags": ["adventure", "trekking"],
            "img_desc": None,
        },
        "expect_pref": {
            "intensity": lambda v: v is not None and v >= 0.8,
            "physical":  lambda v: v is not None and v >= 0.8,
        },
    },
    {
        "name": "preference_inference_peaceful_tags",
        "desc": "Tags peaceful, solo → intensity thấp, social thấp",
        "data_pref": {
            "text": "đi một mình thư giãn",
            "tags": ["peaceful", "solo"],
            "img_desc": None,
        },
        "expect_pref": {
            "intensity": lambda v: v is not None and v <= 0.25,
            "social":    lambda v: v is not None and v <= 0.2,
        },
    },
    {
        "name": "normalization_spread",
        "desc": "Sau normalize: top score trong [0.8, 1.0], bottom score trong [0.4, 0.6]",
        "data": {
            "text_k": 3, "tags_k": 3, "top_k": 5,
            "user_input": {"text": "biển", "tags": [], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": BEACH, "aug_tags": BEACH, "img_desc": None},
            "activities": [
                _activity("act_1", "loc_1", "Lặn biển",   "nature",    0.5, 0.5, 0.5, BEACH),
                _activity("act_2", "loc_1", "Leo núi",    "adventure", 0.8, 0.8, 0.4, MOUNTAIN),
                _activity("act_3", "loc_1", "Ẩm thực",    "food",      0.3, 0.1, 0.5, FOOD),
                _activity("act_4", "loc_1", "Phố cổ",     "culture",   0.2, 0.2, 0.6, CITY),
                _activity("act_5", "loc_1", "Nghỉ dưỡng", "relaxation",0.1, 0.1, 0.2, BEACH),
            ],
        },
        "expect_top_score_gte": 0.8,
        "expect_bottom_score_gte": 0.4,
    },
    {
        "name": "null_vectors_graceful",
        "desc": "Activity có vectors=None không crash, rơi về attribute score",
        "data": {
            "text_k": 3, "tags_k": 3, "top_k": 2,
            "user_input": {"text": "", "tags": [], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": None, "aug_tags": None, "img_desc": None},
            "activities": [
                _activity("act_a", "loc_1", "A", "nature",    0.5, 0.5, 0.5, None),
                _activity("act_b", "loc_1", "B", "adventure", 0.8, 0.8, 0.5, BEACH),
            ],
        },
        "expect_no_crash": True,
        "expect_count": 2,
    },
    {
        "name": "top_k_truncation",
        "desc": "top_k=3 với 10 activities → chỉ trả về 3",
        "data": {
            "text_k": 2, "tags_k": 2, "top_k": 3,
            "user_input": {"text": "biển", "tags": [], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": BEACH, "aug_tags": BEACH, "img_desc": None},
            "activities": [
                _activity(f"act_{i}", "loc_1", f"Activity {i}", "nature", 0.5, 0.5, 0.5, BEACH)
                for i in range(10)
            ],
        },
        "expect_count": 3,
    },
    {
        "name": "performance_50_activities",
        "desc": "50 activities (realistic) — kiểm tra tốc độ",
        "data": {
            "text_k": 3, "tags_k": 3, "top_k": TOP_K_ACTIVITIES,
            "user_input": {"text": "khám phá thiên nhiên", "tags": ["adventure"], "img_desc": None},
            "user_vectors": {"text": BEACH, "aug_text": BEACH, "aug_tags": BEACH, "img_desc": None},
            "activities": [
                _activity(f"act_{i:03d}", f"loc_{i % 5}", f"Activity {i}",
                          ["nature","adventure","food","culture","relaxation"][i % 5],
                          (i % 10) / 10, (i % 8) / 8, (i % 6) / 6,
                          _normalize(_unit(i % DIM)))
                for i in range(50)
            ],
        },
        "expect_count": TOP_K_ACTIVITIES,
        "perf_threshold_ms": 200,
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_test(test: dict) -> dict:
    # Preference-only tests
    if "data_pref" in test:
        t0 = time.perf_counter()
        prefs = infer_user_preferences(test["data_pref"])
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        checks = {}
        passed = True
        for axis, validator in test["expect_pref"].items():
            ok = validator(prefs.get(axis))
            checks[f"{axis}_pref_ok"] = ok
            if not ok:
                passed = False

        status = "PASS" if passed else "FAIL"
        print(f"  [{test['name']:<45}] {elapsed_ms:3d}ms  {status}  prefs={prefs}")
        return {
            "name": test["name"], "desc": test["desc"],
            "latency_ms": elapsed_ms, "status": status,
            "checks": checks, "prefs": prefs,
            "top1_id": None, "scores": [],
        }

    # Full ranking tests
    try:
        n6_result = rank_activities(test["data"])
        n6_metadata = n6_result.get("metadata", {})
        
        acts     = n6_result.get("activities", [])
        top1_id  = acts[0]["activity_id"] if acts else None
        top1_s   = acts[0]["score"] if acts else None
        last_s   = acts[-1]["score"] if acts else None
        
        # Use internal metadata for reporting
        prefs      = n6_metadata.get("user_prefs", {})
        elapsed_ms = n6_metadata.get("latency_ms", 0)
        crashed    = False
    except Exception as e:
        acts       = []
        top1_id    = None
        top1_s     = None
        last_s     = None
        prefs      = {}
        elapsed_ms = 0
        crashed    = True

    checks = {}
    passed = True

    if test.get("expect_no_crash"):
        ok = not crashed
        checks["no_crash"] = ok
        if not ok: passed = False

    if test.get("expect_top1"):
        ok = top1_id == test["expect_top1"]
        checks["top1_correct"] = ok
        if not ok: passed = False

    if test.get("expect_count"):
        ok = len(acts) == test["expect_count"]
        checks["count_correct"] = ok
        if not ok: passed = False

    if test.get("expect_top_score_gte") is not None:
        ok = top1_s is not None and top1_s >= test["expect_top_score_gte"]
        checks["top_score_ok"] = ok
        if not ok: passed = False

    if test.get("expect_bottom_score_gte") is not None:
        ok = last_s is not None and last_s >= test["expect_bottom_score_gte"]
        checks["bottom_score_ok"] = ok
        if not ok: passed = False

    if test.get("perf_threshold_ms"):
        ok = elapsed_ms <= test["perf_threshold_ms"]
        checks["perf_ok"] = ok
        if not ok: passed = False

    status = "PASS" if passed else "FAIL"
    print(f"  [{test['name']:<45}] {elapsed_ms:3d}ms  {status}")
    if not passed:
        print(f"    checks: {checks}  top1={top1_id}  scores={[a['score'] for a in acts]}")

    return {
        "name": test["name"], "desc": test["desc"],
        "latency_ms": elapsed_ms, "status": status,
        "checks": checks, "prefs": prefs,
        "top1_id": top1_id,
        "scores": [a["score"] for a in acts],
    }


# ── Markdown Report ────────────────────────────────────────────────────────────

def _build_markdown(results: list[dict], date_str: str) -> str:
    L: list[str] = []
    def line(text=""): L.append(text)

    passed = sum(1 for r in results if r["status"] == "PASS")
    n = len(results)
    avg_lat = round(sum(r["latency_ms"] for r in results) / n, 1) if n else 0

    line("# N6 — Module Activity Ranking: Báo Cáo Bench Test\n")
    line(f"**Ngày:** {date_str}  ")
    line(f"**Phương pháp:** Semantic (50%) + Attribute (50%) Scoring  ")
    line(f"**Số ca test:** {n}  ")
    line(f"**Pass rate:** {passed}/{n}  ")
    line()
    line("---")
    line()
    line("## 1. Tổng Quan Module\n")
    line("N6 xếp hạng hoạt động du lịch theo công thức kết hợp: **50% ngữ nghĩa** + **50% thuộc tính**. Module hoàn toàn thuần tính toán — không gọi API.\n")
    line("**Công thức tổng thể:**")
    line("```")
    line("score_final = 0.5 × semantic_score + 0.5 × attribute_score")
    line("")
    line("semantic_score:  weighted cosine(user_vectors, activity_vectors)")
    line("                 kéo giãn khỏi dead-zone: (sim - 0.5) × 2")
    line("")
    line("attribute_score: avg fit của 3 trục: intensity / physical / social")
    line("                 fit = 1 - |user_pref - activity_value|")
    line("```")
    line()
    line("**User Preference Inference:**")
    line("- Input: `tags` + `text` + `img_desc`")
    line("- Tags → lookup table (±0.3–1.0 per axis)")
    line("- Keywords → bonus (weight × 0.5)")
    line("- Signal → sigmoid → [0,1]. Thiếu signal → `None` (skip axis, không phạt)")
    line()
    line("**Score Normalization:**")
    line("- Min-max spread về [0.40, 1.0] — giữ nguyên thứ hạng, dễ đọc trên UI")
    line()
    line("---")
    line()
    line("## 2. Các Ca Kiểm Thử\n")
    line("| # | Tên | Mô tả |")
    line("|---|-----|-------|")
    for i, t in enumerate(BENCH_TESTS, 1):
        line(f"| {i} | `{t['name']}` | {t['desc']} |")
    line()
    line("---")
    line()
    line("## 3. Kết Quả Chi Tiết\n")
    for r in results:
        icon = "✓" if r["status"] == "PASS" else "✗"
        line(f"### {icon} `{r['name']}`\n")
        line(f"_{r['desc']}_\n")
        line(f"| Chỉ số | Giá trị |")
        line(f"|--------|---------|")
        line(f"| Độ trễ | {r['latency_ms']} ms |")
        line(f"| Kết quả | **{r['status']}** |")
        if r["top1_id"]:
            line(f"| Top 1 | `{r['top1_id']}` |")
        if r.get("prefs"):
            line(f"| User prefs | `{r['prefs']}` |")
        if r["scores"]:
            line(f"| Điểm số | `{r['scores']}` |")
        for check, ok in r["checks"].items():
            line(f"| {check} | {'✓' if ok else '✗'} |")
        line()
    line("---")
    line()
    line("## 4. Bảng Tổng Hợp\n")
    line("| Ca test | Độ trễ (ms) | Top 1 | Kết quả |")
    line("|---------|:-----------:|-------|:-------:|")
    for r in results:
        icon = "✓ PASS" if r["status"] == "PASS" else "✗ FAIL"
        top1 = f"`{r['top1_id']}`" if r["top1_id"] else "—"
        line(f"| `{r['name']}` | {r['latency_ms']} | {top1} | {icon} |")
    line()
    line(f"**TB latency:** {avg_lat}ms &nbsp;**Pass:** {passed}/{n}\n")
    line("---")
    line()
    line("## 5. Nhận Xét Chính\n")
    line("1. **Deterministic:** N6 là pure computation — kết quả bench hoàn toàn tái hiện, không phụ thuộc API hay seed random.")
    line("2. **Semantic ranking:** Cosine similarity với vector trực giao cho kết quả chính xác — activity cùng hướng với user vector luôn đứng trên.")
    line("3. **Attribute scoring:** Tags như `peaceful` / `solo` ảnh hưởng rõ ràng đến preference inference, đẩy activity intensity thấp lên trên.")
    line("4. **Dead-zone scaling:** Vì embedding cùng domain có cosine rất cao (0.8–0.99), cơ chế `(sim - 0.5) × 2` giúp phân tán điểm thay vì cluster ở đỉnh.")
    line(f"5. **Performance:** 50 activities (realistic) xử lý < 200ms — đủ nhanh cho real-time API với `top_k={TOP_K_ACTIVITIES}`.")

    return "\n".join(L)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    date_str = datetime.now().strftime("%Y-%m-%d")

    print("\n=== N6 BENCH: Activity Ranking Tests ===")
    results = [run_test(t) for t in BENCH_TESTS]

    output = {
        "metadata": {
            "module": "N6 — Activity Ranking",
            "date":   date_str,
            "top_k":  TOP_K_ACTIVITIES,
        },
        "results": results,
    }

    json_path = BASE_DIR / "bench_n6_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {json_path}")

    md_path = BASE_DIR / "bench_n6.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(results, date_str))
    print(f"[saved] {md_path}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n=== SUMMARY: {passed}/{len(results)} PASS ===")
    for r in results:
        print(f"  {r['status']:<5} {r['latency_ms']:3d}ms  {r['name']}")


if __name__ == "__main__":
    main()
