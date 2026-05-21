# N6 — Module Activity Ranking: Báo Cáo Bench Test

**Ngày:** 2026-05-21  
**Phương pháp:** Semantic (50%) + Attribute (50%) Scoring  
**Số ca test:** 8  
**Pass rate:** 8/8  

---

## 1. Tổng Quan Module

N6 xếp hạng hoạt động du lịch theo công thức kết hợp: **50% ngữ nghĩa** + **50% thuộc tính**. Module hoàn toàn thuần tính toán — không gọi API.

**Công thức tổng thể:**
```
score_final = 0.5 × semantic_score + 0.5 × attribute_score

semantic_score:  weighted cosine(user_vectors, activity_vectors)
                 kéo giãn khỏi dead-zone: (sim - 0.5) × 2

attribute_score: avg fit của 3 trục: intensity / physical / social
                 fit = 1 - |user_pref - activity_value|
```

**User Preference Inference:**
- Input: `tags` + `text` + `img_desc`
- Tags → lookup table (±0.3–1.0 per axis)
- Keywords → bonus (weight × 0.5)
- Signal → sigmoid → [0,1]. Thiếu signal → `None` (skip axis, không phạt)

**Score Normalization:**
- Min-max spread về [0.40, 1.0] — giữ nguyên thứ hạng, dễ đọc trên UI

---

## 2. Các Ca Kiểm Thử

| # | Tên | Mô tả |
|---|-----|-------|
| 1 | `semantic_beach_user_ranks_beach_activity_first` | User vector beach → activity về biển phải đứng #1 |
| 2 | `attribute_relaxed_user_avoids_high_intensity` | User 'yên bình' → activity intensity thấp phải lên trên |
| 3 | `preference_inference_adventure_tags` | Tags adventure+trekking → intensity cao, physical cao |
| 4 | `preference_inference_peaceful_tags` | Tags peaceful, solo → intensity thấp, social thấp |
| 5 | `normalization_spread` | Sau normalize: top score trong [0.8, 1.0], bottom score trong [0.4, 0.6] |
| 6 | `null_vectors_graceful` | Activity có vectors=None không crash, rơi về attribute score |
| 7 | `top_k_truncation` | top_k=3 với 10 activities → chỉ trả về 3 |
| 8 | `performance_50_activities` | 50 activities (realistic) — kiểm tra tốc độ |

---

## 3. Kết Quả Chi Tiết

### ✓ `semantic_beach_user_ranks_beach_activity_first`

_User vector beach → activity về biển phải đứng #1_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| Top 1 | `act_snorkel` |
| User prefs | `{'intensity': None, 'physical': None, 'social': None}` |
| Điểm số | `[0.9441, 0.6969, 0.6969]` |
| top1_correct | ✓ |

### ✓ `attribute_relaxed_user_avoids_high_intensity`

_User 'yên bình' → activity intensity thấp phải lên trên_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| Top 1 | `act_relax` |
| User prefs | `{'intensity': 0.214, 'physical': 0.343, 'social': 0.389}` |
| Điểm số | `[0.8903, 0.8673]` |
| top1_correct | ✓ |

### ✓ `preference_inference_adventure_tags`

_Tags adventure+trekking → intensity cao, physical cao_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| User prefs | `{'intensity': 0.881, 'physical': 0.881, 'social': None}` |
| intensity_pref_ok | ✓ |
| physical_pref_ok | ✓ |

### ✓ `preference_inference_peaceful_tags`

_Tags peaceful, solo → intensity thấp, social thấp_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| User prefs | `{'intensity': 0.25, 'physical': 0.343, 'social': 0.154}` |
| intensity_pref_ok | ✓ |
| social_pref_ok | ✓ |

### ✓ `normalization_spread`

_Sau normalize: top score trong [0.8, 1.0], bottom score trong [0.4, 0.6]_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| Top 1 | `act_1` |
| User prefs | `{'intensity': None, 'physical': None, 'social': None}` |
| Điểm số | `[0.9441, 0.9441, 0.6969, 0.6969, 0.6969]` |
| top_score_ok | ✓ |
| bottom_score_ok | ✓ |

### ✓ `null_vectors_graceful`

_Activity có vectors=None không crash, rơi về attribute score_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 0 ms |
| Kết quả | **PASS** |
| Top 1 | `act_b` |
| User prefs | `{'intensity': None, 'physical': None, 'social': None}` |
| Điểm số | `[0.9441, 0.9031]` |
| no_crash | ✓ |
| count_correct | ✓ |

### ✓ `top_k_truncation`

_top_k=3 với 10 activities → chỉ trả về 3_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 5 ms |
| Kết quả | **PASS** |
| Top 1 | `act_7` |
| User prefs | `{'intensity': None, 'physical': None, 'social': None}` |
| Điểm số | `[0.9441, 0.9441, 0.9441]` |
| count_correct | ✓ |

### ✓ `performance_50_activities`

_50 activities (realistic) — kiểm tra tốc độ_

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 16 ms |
| Kết quả | **PASS** |
| Top 1 | `act_000` |
| User prefs | `{'intensity': 0.731, 'physical': 0.69, 'social': None}` |
| Điểm số | `[0.8478, 0.8139, 0.8139, 0.8081, 0.7968]` |
| count_correct | ✓ |
| perf_ok | ✓ |

---

## 4. Bảng Tổng Hợp

| Ca test | Độ trễ (ms) | Top 1 | Kết quả |
|---------|:-----------:|-------|:-------:|
| `semantic_beach_user_ranks_beach_activity_first` | 0 | `act_snorkel` | ✓ PASS |
| `attribute_relaxed_user_avoids_high_intensity` | 0 | `act_relax` | ✓ PASS |
| `preference_inference_adventure_tags` | 0 | — | ✓ PASS |
| `preference_inference_peaceful_tags` | 0 | — | ✓ PASS |
| `normalization_spread` | 0 | `act_1` | ✓ PASS |
| `null_vectors_graceful` | 0 | `act_b` | ✓ PASS |
| `top_k_truncation` | 5 | `act_7` | ✓ PASS |
| `performance_50_activities` | 16 | `act_000` | ✓ PASS |

**TB latency:** 2.6ms &nbsp;**Pass:** 8/8

---

## 5. Nhận Xét Chính

1. **Deterministic:** N6 là pure computation — kết quả bench hoàn toàn tái hiện, không phụ thuộc API hay seed random.
2. **Semantic ranking:** Cosine similarity với vector trực giao cho kết quả chính xác — activity cùng hướng với user vector luôn đứng trên.
3. **Attribute scoring:** Tags như `peaceful` / `solo` ảnh hưởng rõ ràng đến preference inference, đẩy activity intensity thấp lên trên.
4. **Dead-zone scaling:** Vì embedding cùng domain có cosine rất cao (0.8–0.99), cơ chế `(sim - 0.5) × 2` giúp phân tán điểm thay vì cluster ở đỉnh.
5. **Performance:** 50 activities (realistic) xử lý < 200ms — đủ nhanh cho real-time API với `top_k=5`.