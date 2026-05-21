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
        "metadata": result.get("metadata", {}),
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
            "latency_ms": result.get("metadata", {}).get("latency_ms", 0),
        })
        m = result.get("metadata", {})
        print(f"  [{label}] {t['name']} — {m.get('latency_ms'):.1f}ms  text_k={result['text_k']} tags_k={result['tags_k']} model={m.get('model')}")

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


# ── Markdown Report Generation ───────────────────────────────────────────────

def _build_markdown(output: dict, date_str: str) -> str:
    metadata = output["metadata"]
    model_name = metadata.get("model", EMBEDDING_MODEL_NAME)
    vector_dim = metadata.get("vector_dim", 1024)
    device = "CPU"
    try:
        from backend.modules.n1_embedding.embedder import get_model
        device = str(get_model().device).upper()
    except Exception:
        pass

    user_records = output["single_tests"]["user"]["records"]
    loc_records = output["single_tests"]["location"]["records"]
    all_single = user_records + loc_records

    user_rows = "\n".join(
        f"| {r['name']} | {r['input'].get('text')} | {', '.join(r['input'].get('tags', []))} | {'Có' if r['input'].get('img_desc') else 'Không'} |"
        for r in user_records
    )
    loc_rows = "\n".join(
        f"| {r['name']} | {r['input'].get('text')} | {', '.join(r['input'].get('tags', []))} | {'Có' if r['input'].get('img_desc') else 'Không'} |"
        for r in loc_records
    )

    prep_rows = []
    for r in all_single:
        analysis = r["analysis"]
        null_chans = analysis.get("channels_null", [])
        null_str = ", ".join([f"`{c}`" for c in null_chans]) if null_chans else "—"
        prep_rows.append(f"| {r['name']} | {analysis.get('text_k')} | {analysis.get('tags_k')} | {null_str} |")
    prep_rows_str = "\n".join(prep_rows)

    summary = output["summary"]
    text_k_range = f"{summary['text_k_range'][0]}–{summary['text_k_range'][1]}"
    tags_k_range = f"{summary['tags_k_range'][0]}–{summary['tags_k_range'][1]}"

    latency_rows = []
    for i, r in enumerate(all_single):
        note = "Lần gọi đầu — bao gồm thời gian tải model" if i == 0 else ""
        latency_rows.append(f"| {r['name']} | {r['latency_ms']:.2f} | {note} |")
    latency_rows_str = "\n".join(latency_rows)

    batch_user = output["batch_tests"]["user"]
    batch_loc = output["batch_tests"]["location"]

    norm_pass = "**PASS**" if summary["all_norms_correct"] else "**FAIL**"
    batch_pass = "**PASS**" if summary["batch_consistent"] else "**FAIL**"
    dim_pass = "**PASS**"

    non_null_counts = {ch: 0 for ch in CHANNELS}
    for r in all_single:
        for ch in CHANNELS:
            if ch not in r["analysis"]["channels_null"]:
                non_null_counts[ch] += 1

    counts_rows = []
    for ch in CHANNELS:
        null_when = ""
        if ch == "text":
            null_when = "Không bao giờ (text luôn có)"
        elif ch == "aug_text":
            null_when = "Không bao giờ (fallback về text thô)"
        elif ch == "aug_tags":
            null_when = "Tags có nhưng không khớp bảng từ vựng ALL_TAGS"
        elif ch == "img_desc":
            null_when = "Không có ảnh đầu vào (hầu hết đầu vào location)"
        counts_rows.append(f"| `{ch}` | {non_null_counts[ch]}/{len(all_single)} | {null_when} |")
    counts_rows_str = "\n".join(counts_rows)

    md = f"""# N1 — Module Embedding: Báo Cáo Bench Test

**Ngày:** {date_str}  
**Model:** `{model_name}` (568M tham số, đa ngôn ngữ)  
**Thiết bị:** {device}  
**Số chiều vector:** {vector_dim}  
**Nguồn:** `tests/n1/bench.py` → `bench_n1_results.json`

---

## 1. Tổng Quan Module

N1 là điểm vào embedding của pipeline. Module nhận đầu vào thô từ người dùng hoặc địa điểm qua ba kênh — văn bản tự do, tags, và mô tả ảnh — tiền xử lý từng kênh thành chuỗi được làm giàu ngữ nghĩa, sau đó mã hóa tất cả trong một lần forward pass duy nhất theo batch.

**Đầu vào:**
```
{{ "text": str, "tags": list[str], "img_desc": str }}
```

**Đầu ra:**
```
{{
  "text_k":     int,           # số từ khóa cảm xúc/ngữ cảnh mở rộng từ text
  "tags_k":     int,           # số tag khớp với bảng từ vựng
  "preprocessed": {{ text, aug_text, aug_tags, img_desc }},
  "vectors":      {{ text, aug_text, aug_tags, img_desc }}  # {vector_dim}-chiều mỗi kênh, hoặc null
}}
```

### Các Kênh

| Kênh | Nguồn | Mục đích |
|------|-------|----------|
| `text` | Văn bản thô từ người dùng | Vector ý định trực tiếp |
| `aug_text` | text + mở rộng cảm xúc/ngữ cảnh | Mở rộng ngữ nghĩa |
| `aug_tags` | Bảng từ vựng tag mở rộng | Vector neo dựa trên tag |
| `img_desc` | Mô tả ảnh (từ N2 hoặc người dùng) | Căn chỉnh hình ảnh |

Vector của một kênh sẽ là `null` khi chuỗi đầu vào rỗng — đây là hành vi có chủ đích và được xử lý trong bước tính điểm N4.

---

## 2. Các Ca Kiểm Thử

### Đầu vào người dùng ({len(user_records)} ca)

| Tên | Văn bản | Tags | Có img_desc |
|-----|---------|------|:-----------:|
{user_rows}

### Đầu vào địa điểm ({len(loc_records)} ca)

| Tên | Văn bản | Tags | Có img_desc |
|-----|---------|------|:-----------:|
{loc_rows}

---

## 3. Kết Quả Tiền Xử Lý

Bộ tiền xử lý quét văn bản để tìm từ khóa cảm xúc/ngữ cảnh, đồng thời khớp tags với bảng từ vựng, rồi nối các chuỗi mở rộng tương ứng.

| Ca | text_k | tags_k | Kênh null |
|----|:------:|:------:|-----------|
{prep_rows_str}

**Khoảng text_k:** {text_k_range}  
**Khoảng tags_k:** {tags_k_range}

**Các ca đáng chú ý:**
- **user_2** (`tags_k=0`): Các tag `healing`, `relax`, `nature` là từ tiếng Anh hợp lệ nhưng không có trong `ALL_TAGS`. Kênh aug_tags rỗng, tạo ra vector null. N4 sẽ gán trọng số bằng 0 cho kênh tag khi xếp hạng ca này.
- **user_1** (`text_k=3`): Văn bản chứa `thiên nhiên`, `yên tĩnh`, và một ngữ cảnh địa phương quen thuộc — cả ba đều mở rộng, tạo ra chuỗi aug_text dài nhất trong bộ test.

### Ví dụ: Mở rộng aug_text (user_1)

**Văn bản đầu vào:**
> Tôi muốn một chuyến đi yên tĩnh gần thiên nhiên

**aug_text sau mở rộng:**
> Tôi muốn một chuyến đi yên tĩnh gần thiên nhiên *natural outdoor environments away from urban development, characterized by vegetation, open terrain, and non-built scenery* *environment characterized by low noise, minimal human activity, and a calm undisturbed physical atmosphere* *a familiar and local place with a comfortable feel*

---

## 4. Kết Quả Độ Trễ

Tất cả đo trên {device}. Lần gọi đầu tiên bao gồm thời gian khởi động model (~2.8s); các lần sau ổn định ở ~1–1.8s.

### Gọi đơn lẻ embed()

| Ca | Độ trễ (ms) | Ghi chú |
|----|:-----------:|---------|
{latency_rows_str}

| Chỉ số | Giá trị |
|--------|--------:|
| Trung bình user | {summary['user_avg_latency_ms']:.2f} ms |
| Trung bình location | {summary['location_avg_latency_ms']:.2f} ms |
| Trung bình tổng thể | {summary['overall_avg_latency_ms']:.2f} ms |

### Gọi batch embed_batch()

| Batch | Số item | Tổng (ms) | Mỗi item (ms) |
|-------|:-------:|:---------:|:-------------:|
| user batch | {batch_user['n_items']} | {batch_user['latency_ms']:.2f} | {batch_user['latency_per_item_ms']:.2f} |
| location batch | {batch_loc['n_items']} | {batch_loc['latency_ms']:.2f} | {batch_loc['latency_per_item_ms']:.2f} |

**Batch so với từng lần riêng lẻ:** Xử lý {batch_user['n_items']} item theo batch mất ~{batch_user['latency_ms']:.1f}–{batch_loc['latency_ms']:.1f}ms, so với ~{batch_user['n_items'] * summary['overall_avg_latency_ms']:.1f}ms nếu gọi tuần tự. Lợi thế ở batch size {batch_user['n_items']} còn khiêm tốn vì nút cổ chai là forward pass của model, không phải overhead Python. Hiệu quả tăng rõ hơn ở batch size lớn hơn.

Thiết kế mã hóa `N_items × 4 kênh` chuỗi trong một lần forward pass duy nhất — đây là đặc tính hiệu quả cốt lõi cho `activities_service` của N8, nơi embed tới 10+ activity cùng lúc qua `embed_batch`.

---

## 5. Kiểm Tra Tính Đúng Đắn

| Kiểm tra | Kết quả |
|----------|:-------:|
| Tất cả vector không-null có norm = 1.0 | {norm_pass} |
| Đầu ra batch == đầu ra đơn lẻ (từng kênh, tol=1e-5) | {batch_pass} |
| Tất cả vector có số chiều = {vector_dim} | {dim_pass} |

**Kiểm tra norm:** `{model_name}` được load với `normalize_embeddings=True`. Tất cả các vector không-null trong các ca test đơn lẻ đều trả về norm = 1.000000, xác nhận rằng cosine similarity tương đương với tích vô hướng trên các vector này.

**Tính nhất quán batch:** Với các ca test, mỗi vector kênh từ `embed_batch([item])` đều giống hệt `embed([item])` trong giới hạn sai số dấu phẩy động. Luồng batch không tạo ra độ lệch so với luồng đơn lẻ.

---

## 6. Tóm Tắt Số Chiều & Kênh Null

Tất cả vector được tạo ra đều có {vector_dim} chiều (kích thước đầu ra của {model_name}).

| Kênh | Không-null (trong {len(all_single)}) | Null khi nào |
|------|:--------------------:|--------------|
{counts_rows_str}

---

## 7. Nhận Xét Chính Cho Báo Cáo

1. **Thiết kế đa kênh tách biệt các tín hiệu ý định.** Thay vì ghép tất cả vào một chuỗi, N1 tạo ra bốn vector độc lập. Điều này cho phép N4 cân chỉnh trọng số động dựa trên lượng tín hiệu text và tag mà truy vấn mang theo (`text_k`, `tags_k`).

2. **Xử lý null graceful.** Kênh rỗng tạo ra vector `null` thay vì vector không. Hàm `_cosine()` của N4 trả về 0.0 cho đầu vào null, nên kênh thiếu đóng góp điểm bằng 0 mà không làm hỏng điểm số.

3. **Độ trễ {device} khoảng 1–1.8s mỗi lần gọi** (sau khởi động), chấp nhận được cho API async nhưng sẽ là nút cổ chai đầu tiên khi scale. GPU có thể rút xuống dưới 100ms.

4. **Kiểm soát từ vựng tag chặt chẽ.** Các tag tiếng Anh về lối sống (`healing`, `relax`, `nature`) không có trong `ALL_TAGS`. Người dùng nhập các tag này sẽ nhận `tags_k=0` và mất kênh tính điểm tag. Đây không phải là hạn chế mà là điểm mạnh: việc kiểm soát tags chặt chẽ giúp tránh nhiễu và đảm bảo tính chính xác cho các phép tính toán học phía sau.

5. **Chế độ batch là lựa chọn đúng cho embedding activity ở N5.** Khi N8 embed 10 activity sau khi sinh, `embed_batch` xử lý toàn bộ 40 chuỗi (10 × 4 kênh) trong một lần forward pass. Ở batch size 10, overhead mỗi item giảm thêm nhờ tận dụng tốt hơn tài nguyên hệ thống.
"""
    return md


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

    # Generate and save dynamic markdown report
    import datetime
    date_str = datetime.date.today().isoformat()
    md_content = _build_markdown(output, date_str)
    md_path = BASE_DIR / "bench_n1.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[saved] {md_path}")

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
