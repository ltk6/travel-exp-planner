"""
bench_n6_profiles.py — Xác thực N6 rank khác nhau cho profile đối lập.

Kịch bản:
  1. Generate 1 bộ activities (qua N5) cho 1 location cố định.
  2. Chạy N6 ranking với 2 user profile ĐỐI LẬP:
       A) solo + peaceful (intensity/physical/social đều muốn thấp)
       B) family + adventure (intensity/physical/social đều muốn cao)
  3. So sánh top-5 của 2 profile — nếu N6 attribute scoring hoạt động,
     thứ hạng phải khác nhau rõ rệt.

Không cần khởi động backend — gọi module trực tiếp.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_here    = Path(__file__).resolve().parent
_root    = _here.parent
_backend = _root / "backend"
for p in (str(_root), str(_backend)):
    if p not in sys.path:
        sys.path.insert(0, p)

from modules.n5_activity_generation import generate_activities
from modules.n5_activity_generation import cache as llm_cache
from modules.n6_activity_ranking import rank_activities, infer_user_preferences
from modules.n1_embedding import embed


LOCATION = {
    "location_id": "loc_hoi_an",
    "metadata": {
        "name": "Hội An",
        "description": "Phố cổ với kiến trúc truyền thống, ẩm thực nổi tiếng, đèn lồng rực rỡ",
        "tags": ["heritage", "food", "culture"],
    },
}

PROFILES = {
    "solo_peaceful": {
        "text": "Tôi muốn chuyến đi yên bình một mình, ngắm cảnh chậm rãi",
        "tags": ["solo", "peaceful", "photography"],
    },
    "family_adventure": {
        "text": "Gia đình đi chơi vui nhộn, muốn trải nghiệm mạo hiểm",
        "tags": ["family", "adventure", "trekking"],
    },
}


def _embed_user(text: str, tags: list) -> dict:
    """Dùng N1 để embed user input → user_vectors."""
    out = embed([{"text": text, "tags": tags, "img_desc": ""}])[0]
    v = out.get("vectors", {}) or {}
    return {
        "text_k":       out.get("text_k", 0),
        "tags_k":       out.get("tags_k", 0),
        "user_vectors": {
            "text":     list(v.get("text") or []),
            "aug_text": list(v.get("aug_text") or []),
            "aug_tags": list(v.get("aug_tags") or []),
            "img_desc": list(v.get("img_desc") or []),
        },
    }


def _embed_activities(activities: list) -> list:
    """Embed text+tag cho từng activity để N6 tính semantic score."""
    inputs = []
    for act in activities:
        meta = act.get("metadata", {})
        act_text = f"{meta.get('name', '')} - {meta.get('description', '')}".strip(" -")
        act_tags = []
        if meta.get("activity_type"):
            act_tags.append(meta["activity_type"])
        if meta.get("activity_subtype"):
            act_tags.append(meta["activity_subtype"])
        inputs.append({"text": act_text, "tags": act_tags, "img_desc": ""})

    results = embed(inputs)
    for act, res in zip(activities, results):
        v = res.get("vectors", {}) or {}
        act["vectors"] = {
            "text": list(v.get("text") or []),
            "tag":  list(v.get("aug_tags") or []),
        }
    return activities


def run():
    print(f"\n=== Generating activities for {LOCATION['metadata']['name']} (N5) ===")
    llm_cache.clear()
    n5_out = generate_activities({
        "user": {"text": "", "img_desc": "", "tags": []},
        "locations": [LOCATION],
        "constraints": {},
        "target_count": 10,
    })
    activities = n5_out.get("activities", [])
    print(f"  → {len(activities)} activities generated")

    print("\n=== Embedding activities (N1) ===")
    activities = _embed_activities(activities)
    print(f"  → {len(activities)} activities embedded")

    results = {}
    for profile_name, profile in PROFILES.items():
        print(f"\n=== Profile: {profile_name} ===")
        print(f"  text: {profile['text']!r}")
        print(f"  tags: {profile['tags']}")

        prefs = infer_user_preferences({**profile, "img_desc": ""})
        print(f"  inferred prefs: intensity={prefs['intensity']} "
              f"physical={prefs['physical']} social={prefs['social']}")

        user_data = _embed_user(profile["text"], profile["tags"])

        ranked = rank_activities({
            "text_k":       user_data["text_k"],
            "tags_k":       user_data["tags_k"],
            "user_input":   {**profile, "img_desc": ""},
            "user_vectors": user_data["user_vectors"],
            "context":      {"time_of_day": "afternoon"},
            "activities":   activities,
            "top_k":        5,
        })

        results[profile_name] = ranked["activities"]
        print(f"  Top 5 ranked:")
        for i, a in enumerate(ranked["activities"], 1):
            act_id = a["activity_id"]
            # Tra metadata để hiển thị tên + 3 axis
            meta = next((x["metadata"] for x in activities if x["activity_id"] == act_id), {})
            print(f"    {i}. [{a['score']:.3f}] {meta.get('name', '?'):<35} "
                  f"int={meta.get('intensity', '?'):.2f} "
                  f"phys={meta.get('physical_level', 0):.2f} "
                  f"soc={meta.get('social_level', 0):.2f}")

    # ── Compare ────────────────────────────────────────────────
    print("\n=== COMPARISON ===")
    a_ids = [a["activity_id"] for a in results["solo_peaceful"]]
    b_ids = [a["activity_id"] for a in results["family_adventure"]]
    overlap = set(a_ids) & set(b_ids)
    print(f"Top-5 overlap: {len(overlap)}/5 activities in common")
    print(f"Top-1 same? {a_ids[0] == b_ids[0]}")
    # Spearman-ish: đo mức độ khác nhau của ranking
    if set(a_ids) == set(b_ids):
        displacement = sum(abs(a_ids.index(x) - b_ids.index(x)) for x in a_ids)
        print(f"Rank displacement (same set): {displacement}")
    else:
        print("Rank sets differ — N6 thực sự loại/thêm activity khác giữa 2 profile")


if __name__ == "__main__":
    run()
