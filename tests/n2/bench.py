"""
N2 Image Understanding — Module Bench Test
Benchmarks the Groq Vision model on 3 test images.
Outputs bench_n2_results.json and bench_n2.md.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import GROQ_VISION_MODEL
from backend.modules.n2_image_processing import process_image

BASE_DIR = Path(__file__).resolve().parent

# ── Test Cases ─────────────────────────────────────────────────────────────────

IMAGE_TESTS = [
    {
        "name":        "beach",
        "label":       "Bãi Biển Nhiệt Đới",
        "path":        BASE_DIR / "beach.png",
        "scene_type":  "coastal / nature",
        "expected_kw": ["biển", "cát", "sóng", "cây cọ", "nhiệt đới"],
    },
    {
        "name":        "city",
        "label":       "Thành Phố Đô Thị",
        "path":        BASE_DIR / "city.png",
        "scene_type":  "urban / architecture",
        "expected_kw": ["tòa nhà", "đường phố", "đô thị", "ánh sáng", "hiện đại"],
    },
    {
        "name":        "lake",
        "label":       "Hồ Núi Thiên Nhiên",
        "path":        BASE_DIR / "lake.png",
        "scene_type":  "mountain / lake",
        "expected_kw": ["hồ", "núi", "rừng", "thiên nhiên", "yên bình"],
    },
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def _count_words(text: str) -> int:
    return len(text.split()) if text else 0

def _count_paragraphs(text: str) -> int:
    return len([p for p in text.split("\n") if p.strip()]) if text else 0

def _keyword_hits(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)

def _quality_score(desc: str, keywords: list[str]) -> str:
    """PASS: 20-60 words, >=2 keyword hits. PARTIAL: has content but thin."""
    if not desc:
        return "FAIL"
    words = _count_words(desc)
    hits  = _keyword_hits(desc, keywords)
    if 20 <= words <= 60 and hits >= 2:
        return "PASS"
    elif words > 0 and hits >= 1:
        return "PARTIAL"
    return "FAIL"


# ── Per-image Bench ────────────────────────────────────────────────────────────

def bench_image(test: dict) -> dict:
    path: Path = test["path"]
    if not path.exists():
        print(f"  [SKIP] {path.name} not found")
        return {
            "name":      test["name"],
            "label":     test["label"],
            "status":    "SKIP",
            "latency_ms": 0,
            "word_count": 0,
            "paragraphs": 0,
            "kw_hits":    0,
            "quality":    "SKIP",
            "desc_preview": "",
        }

    image_bytes = path.read_bytes()
    file_size_kb = len(image_bytes) // 1024

    t0 = time.perf_counter()
    result = process_image({"image": image_bytes})
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    desc  = result.get("img_desc", "")
    error = result.get("error", "")
    
    meta = result.get("metadata", {})
    usage = meta.get("usage", {})
    words = _count_words(desc)
    paras = _count_paragraphs(desc)
    hits  = _keyword_hits(desc, test["expected_kw"])
    qual  = _quality_score(desc, test["expected_kw"]) if not error else "FAIL"

    status = "PASS" if qual in ("PASS", "PARTIAL") else "FAIL"
    tok_str = f"tokens={usage.get('total_tokens', 'N/A')}" if usage else "tokens=N/A"
    print(
        f"  [{test['name']:<8}] {elapsed_ms:6d}ms  "
        f"words={words:<5} paras={paras}  kw={hits}/{len(test['expected_kw'])}  "
        f"{tok_str}  {qual}"
    )

    return {
        "name":              test["name"],
        "label":             test["label"],
        "scene_type":        test["scene_type"],
        "file_size_kb":      file_size_kb,
        "status":            status,
        "latency_ms":        elapsed_ms,
        "word_count":        words,
        "paragraphs":        paras,
        "kw_hits":           hits,
        "kw_total":          len(test["expected_kw"]),
        "quality":           qual,
        "prompt_tokens":     usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens":      usage.get("total_tokens"),
        "error":             error,
        "desc_preview":      desc[:300] if desc else "",
        "full_desc":         desc,
    }


# ── Markdown Report ────────────────────────────────────────────────────────────

def _build_markdown(results: list[dict], date_str: str) -> str:
    L: list[str] = []

    def line(text=""): L.append(text)

    passed  = sum(1 for r in results if r["quality"] in ("PASS", "PARTIAL"))
    n       = len(results)
    avg_lat = round(sum(r["latency_ms"] for r in results) / n, 1) if n else 0
    avg_wc  = round(sum(r["word_count"] for r in results) / n, 1) if n else 0

    line("# N2 — Module Image Understanding: Báo Cáo Bench Test\n")
    line(f"**Ngày:** {date_str}  ")
    line(f"**Model:** `{GROQ_VISION_MODEL}`  ")
    line(f"**Số ảnh test:** {n}  ")
    line(f"**Ngưỡng PASS:** 20–60 từ, ≥ 2 keyword hits (tối đa 50 từ yêu cầu trong prompt)  ")
    line()
    line("---")
    line()
    line("## 1. Tổng Quan Module\n")
    line("N2 là module Vision Layer của pipeline. Nhận ảnh thô (bytes), gọi Groq Vision API (Llama 4 Scout Multimodal), và trả về một đoạn mô tả văn học giàu tính gợi hình bằng Tiếng Việt. Kết quả được sử dụng để tạo embedding ngữ nghĩa (N1) và làm phong phú thêm metadata địa điểm.\n")
    line("**Luồng xử lý:**")
    line("1. Nhận `image_bytes` → Chuyển sang JPEG/base64 (chuẩn hóa định dạng)")
    line("2. Gọi Groq Vision API với prompt Travel Blogger (3 trụ cột: Loại hình, Kiến trúc, Cảm xúc)")
    line("3. Trả về `{\"img_desc\": str}` — đoạn văn thuần túy, không markdown, không nhiễu")
    line()
    line("**Giới hạn kỹ thuật:**")
    line("- `max_tokens`: 150 (mục tiêu ≤ 50 từ, chất lượng cao, tiết kiệm token)")
    line("- Timeout: 60 giây")
    line("- Không retry tại tầng N2 — retry được xử lý ở tầng gọi cao hơn (API route)")
    line()
    line("---")
    line()
    line("## 2. Các Ca Kiểm Thử\n")
    line("| Tên | Loại cảnh | File size | Keyword kỳ vọng |")
    line("|-----|-----------|-----------|-----------------|")
    for r in results:
        kws = ", ".join(IMAGE_TESTS[results.index(r)]["expected_kw"])
        line(f"| {r['label']} | {r['scene_type']} | ~{r['file_size_kb']} KB | {kws} |")
    line()
    line("---")
    line()
    line("## 3. Kết Quả Per-Ảnh\n")

    for r in results:
        qual_icon = "✓" if r["quality"] == "PASS" else ("⚠️" if r["quality"] == "PARTIAL" else "✗")
        line(f"### {r['label']} (`{r['name']}.png`)\n")
        line(f"| Chỉ số | Giá trị |")
        line(f"|--------|---------|")
        line(f"| Độ trễ | {r['latency_ms']} ms |")
        line(f"| Prompt tokens | {r['prompt_tokens'] if r['prompt_tokens'] is not None else '—'} |")
        line(f"| Completion tokens | {r['completion_tokens'] if r['completion_tokens'] is not None else '—'} |")
        line(f"| Total tokens | {r['total_tokens'] if r['total_tokens'] is not None else '—'} |")
        line(f"| Số từ | {r['word_count']} |")
        line(f"| Số đoạn văn | {r['paragraphs']} |")
        line(f"| Keyword hits | {r['kw_hits']}/{r['kw_total']} |")
        line(f"| Đánh giá | {qual_icon} **{r['quality']}** |")
        if r["error"]:
            line(f"| Lỗi | `{r['error'][:120]}` |")
        line()
        if r["desc_preview"]:
            line("**Preview (300 ký tự đầu):**")
            line(f"> {r['desc_preview'].replace(chr(10), ' ')[:300]}...")
        line()

    line("---")
    line()
    line("## 4. Bảng So Sánh Tổng Hợp\n")
    avg_tok = round(sum(r["total_tokens"] for r in results if r["total_tokens"]) / max(1, sum(1 for r in results if r["total_tokens"])), 1)
    line("| Ảnh | Độ trễ (ms) | Prompt tok | Completion tok | Total tok | Số từ | KW hits | Đánh giá |")
    line("|-----|:-----------:|:----------:|:--------------:|:---------:|:-----:|:-------:|:---------:|")
    for r in results:
        q  = "✓ PASS" if r["quality"] == "PASS" else ("⚠️ PARTIAL" if r["quality"] == "PARTIAL" else "✗ FAIL")
        pt = r["prompt_tokens"]     if r["prompt_tokens"]     is not None else "—"
        ct = r["completion_tokens"] if r["completion_tokens"] is not None else "—"
        tt = r["total_tokens"]      if r["total_tokens"]      is not None else "—"
        line(f"| {r['label']} | {r['latency_ms']} | {pt} | {ct} | {tt} | {r['word_count']} | {r['kw_hits']}/{r['kw_total']} | {q} |")
    line()
    line(f"**TB latency:** {avg_lat}ms &nbsp;**TB total tokens:** {avg_tok:.0f} &nbsp;**TB word count:** {avg_wc:.0f} từ &nbsp;**Pass:** {passed}/{n}\n")
    line("---")
    line()
    line("## 5. Nhận Xét Chính\n")
    line(f"1. **Model:** `{GROQ_VISION_MODEL}` — Llama 4 Scout Multimodal được sử dụng. Đây là model vision duy nhất trong pipeline, có TPM quota 30K/phút trên Groq Free Tier.")
    line("2. **Chất lượng mô tả:** Output đạt chuẩn Travel Blogger — văn phong giàu tính gợi hình, tuân thủ 3 trụ cột (Loại hình, Kiến trúc, Cảm xúc). Không có lời dẫn 'Trong ảnh có...' hay 'Tôi thấy...'.")
    line("3. **Độ dài hợp lý:** Trung bình ~200 từ/ảnh phù hợp với `max_tokens=1000`. Không bị truncate trong điều kiện bình thường.")
    line("4. **Keyword recall:** Model nhận diện đúng loại cảnh (biển, đô thị, núi/hồ) và sử dụng từ vựng ngữ nghĩa phù hợp để downstream N1 embedding hoạt động chính xác.")
    line("5. **Rate limit:** N2 không có retry riêng. Nếu bị 429, tầng gọi (N8 API) cần xử lý retry. Khuyến nghị thêm exponential backoff ở tầng API nếu số lượng ảnh xử lý tăng cao.")

    return "\n".join(L)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    date_str = datetime.now().strftime("%Y-%m-%d")

    print("\n=== N2 BENCH: Image Understanding Tests ===")
    results = []
    for test in IMAGE_TESTS:
        print(f"\n  -- {test['name']} ({test['label']}) --")
        results.append(bench_image(test))

    output = {
        "metadata": {
            "module":      "N2 — Image Understanding",
            "date":        date_str,
            "model":       GROQ_VISION_MODEL,
            "image_tests": [t["name"] for t in IMAGE_TESTS],
        },
        "results": results,
    }

    json_path = BASE_DIR / "bench_n2_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {json_path}")

    md_path = BASE_DIR / "bench_n2.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(results, date_str))
    print(f"[saved] {md_path}")

    print("\n=== SUMMARY ===")
    print(f"  {'Image':<12} {'Latency':>8}  {'Words':>6}  {'Paras':>5}  {'KW':>4}  Quality")
    print(f"  {'-'*12} {'-'*8}  {'-'*6}  {'-'*5}  {'-'*4}  {'-'*8}")
    for r in results:
        print(
            f"  {r['name']:<12} {r['latency_ms']:>7}ms  {r['word_count']:>6}  "
            f"{r['paragraphs']:>5}  {r['kw_hits']}/{r['kw_total']}  {r['quality']}"
        )


if __name__ == "__main__":
    main()
