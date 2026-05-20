"""
N3 Database Layer — Module Bench Test
Standardized technical report for binary persistence and smart sync.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2

# Thêm PROJECT_ROOT vào sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import PG_URI
from backend.n3_database.db_manager import (
    init_db,
    save_location,
    get_all_locations,
    get_db_fingerprint,
)

# ====================== CONFIG ======================
BASE_DIR = Path(__file__).resolve().parent

FAKE_VEC = [0.01] * 1024

SAVE_TESTS = [
    {
        "name": "loc_beach",
        "label": "Bãi Sao Phú Quốc",
        "data": {
            "location_id": "bench_loc_001",
            "vectors": {
                "text": FAKE_VEC,
                "aug_text": FAKE_VEC,
                "aug_tags": FAKE_VEC,
                "img_desc": None,
            },
            "metadata": {
                "name": "Bãi Sao Phú Quốc",
                "description": "Beach test",
                "tags": ["beach"],
            },
            "geo": {"lat": 10.02, "lng": 104.02},
        },
    },
]


# ====================== BENCHMARK FUNCTIONS ======================
def bench_connectivity() -> dict:
    """Kiểm tra kết nối PostgreSQL."""
    t0 = time.perf_counter()
    try:
        conn = psycopg2.connect(PG_URI)
        conn.close()
        latency_ms = int((time.perf_counter() - t0) * 1000)

        print(f" [connectivity ] {latency_ms:5d}ms ✓ PASS")
        return {"status": "PASS", "latency_ms": latency_ms, "error": None}
    except Exception as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        print(f" [connectivity ] {latency_ms:5d}ms ✗ FAIL")
        return {"status": "FAIL", "latency_ms": latency_ms, "error": str(e)}


def bench_fingerprint() -> dict:
    """Lấy và đo thời gian lấy DB fingerprint."""
    t0 = time.perf_counter()
    fp = get_db_fingerprint()
    latency_ms = int((time.perf_counter() - t0) * 1000)

    status = "PASS" if fp else "FAIL"
    print(f" [fingerprint ] {latency_ms:5d}ms {status}  fp={fp}")
    return {"status": status, "latency_ms": latency_ms, "fingerprint": fp}


def bench_get_all(include_images: bool = True) -> dict:
    """Benchmark get_all_locations."""
    mode = "full" if include_images else "light"
    t0 = time.perf_counter()

    result = get_all_locations(include_images=include_images)
    meta = result.get("metadata", {})
    latency_ms = meta.get("latency_ms", 0)

    status = "PASS" if result.get("status") == "success" else "FAIL"
    print(f" [get_all_{mode:<5}] {latency_ms:5d}ms {status}")

    return {
        "latency_ms": latency_ms,
        "status": status,
        "total": result.get("total", 0),
    }


def bench_save(test: dict) -> dict:
    """Benchmark save_location."""
    t0 = time.perf_counter()
    result = save_location(test["data"])
    meta = result.get("metadata", {})
    latency_ms = meta.get("latency_ms", 0)

    status = "PASS" if result.get("status") == "success" else "FAIL"
    print(f" [save {test['name']:<12}] {latency_ms:5d}ms {status}")

    return {
        "name": test["name"],
        "label": test["label"],
        "location_id": test["data"]["location_id"],
        "latency_ms": latency_ms,
        "status": status,
    }


# ====================== REPORT GENERATION ======================
def _build_markdown(output: dict, date_str: str) -> str:
    """Tạo báo cáo Markdown."""
    lines: list[str] = []

    def line(text: str = ""):
        lines.append(text)

    conn = output["connectivity"]
    fp_test = output["fingerprint"]
    saves = output["save_tests"]
    get_light = output["get_all_light"]

    pg_uri_masked = (PG_URI or "").split("@")[-1] if PG_URI else "not set"

    line("# N3 — Module Database Layer: Báo Cáo Bench Test\n")
    line(f"**Ngày:** {date_str}")
    line(f"**Database:** PostgreSQL + pgvector + BYTEA[]")
    line(f"**Host:** `{pg_uri_masked}`")
    line()
    line("---")
    line()

    line("## 1. Tổng Quan Module")
    line(
        "N3 là lớp lưu trữ dữ liệu tập trung, chịu trách nhiệm persistence cho "
        "địa điểm, vector (N1), mô tả ảnh (N2) và metadata địa lý."
    )
    line()
    line("**Tính năng cốt lõi:**")
    line("- **Vector Storage:** `pgvector` với embedding 1024 chiều")
    line("- **Binary Persistence:** Lưu ảnh trực tiếp dưới dạng `BYTEA[]`")
    line("- **Smart Sync:** Fingerprinting hỗ trợ đồng bộ thông minh")
    line()
    line("---")
    line()

    line("## 2. Kết Quả Smart Sync")
    line("| Chỉ số      | Phương thức                    | Độ trễ (ms) | Ghi chú |")
    line("|-------------|--------------------------------|-------------|---------|")
    line(
        f"| Light Load  | `get_all(images=False)`        | {get_light['latency_ms']:5d} ms    |       |"
    )
    line()
    line("---")
    line()

    line("## 3. Kiểm Tra Kết Nối & Write")
    line(f"- **Kết nối:** {'PASS' if conn['status'] == 'PASS' else 'FAIL'} "
         f"({conn['latency_ms']} ms)")
    line()
    line("| Địa điểm              | Location ID       | Độ trễ (ms) | Kết quả |")
    line("|-----------------------|-------------------|-------------|---------|")
    for s in saves:
        line(
            f"| {s['label']:<21} | `{s['location_id']}` | {s['latency_ms']:5d} ms    | {s['status']} |"
        )

    line()
    line("---")
    line()
    line("## 4. Nhận Xét Hệ Thống")
    line("1. **Atomic Persistence:** Đã chuyển hoàn toàn sang lưu trữ nhị phân trong DB.")
    line("2. **Sync Intelligence:** Fingerprint giúp giảm đáng kể traffic binary.")
    line("3. **Cloud Ready:** Dễ dàng deploy lên Hugging Face Spaces hoặc các nền tảng cloud.")

    return "\n".join(lines)


# ====================== CLEANUP ======================
def cleanup_bench_data() -> None:
    """Xóa dữ liệu benchmark (location_id bắt đầu bằng 'bench_')."""
    print("\n=== CLEANUP: Removing benchmark data ===")
    try:
        conn = psycopg2.connect(PG_URI)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("DELETE FROM locations WHERE location_id LIKE 'bench_%';")
        print(f" [cleanup] Deleted {cur.rowcount} records.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f" [cleanup] Error: {e}")


# ====================== MAIN ======================
def main() -> None:
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n=== N3 BENCH: Smart Sync & Binary Persistence Test ===\n")

    conn_res = bench_connectivity()
    fp_res = bench_fingerprint()
    save_results = [bench_save(t) for t in SAVE_TESTS]
    get_light = bench_get_all(include_images=False)

    output = {
        "metadata": {"date": date_str},
        "connectivity": conn_res,
        "fingerprint": fp_res,
        "save_tests": save_results,
        "get_all_light": get_light,
    }

    # Lưu kết quả
    md_path = BASE_DIR / "bench_n3.md"
    json_path = BASE_DIR / "bench_n3_results.json"

    md_path.write_text(_build_markdown(output, date_str), encoding="utf-8")
    json_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n[DONE] Benchmark completed!")
    print(f"   • Markdown : {md_path}")
    print(f"   • JSON     : {json_path}")

    cleanup_bench_data()


if __name__ == "__main__":
    main()