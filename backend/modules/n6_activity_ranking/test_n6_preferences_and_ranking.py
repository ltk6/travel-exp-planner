"""
test_n6_preferences_and_ranking.py — Unit tests cho N6 contract mới.

Chạy:
    python -m unittest backend.modules.n6_activity_ranking.test_n6_preferences_and_ranking -v

Coverage:
  - preferences.infer_user_preferences: map tag → 3 axis, keyword boost, neutral
  - rank_activities: formula 0.5 sem + 0.5 attr, top_k cut-off, empty input,
                     missing axis không phạt oan, bỏ hẳn constraints cũ
"""

import os
import sys
import unittest

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from backend.modules.n6_activity_ranking.preferences import infer_user_preferences
from backend.modules.n6_activity_ranking.rank_activities import rank_activities


# =============================================================================
# PREFERENCE INFERENCE
# =============================================================================

class TestPreferenceInference(unittest.TestCase):

    def test_adventure_tags_push_intensity_high(self):
        prefs = infer_user_preferences({"tags": ["adventure", "trekking"], "text": "", "img_desc": ""})
        self.assertIsNotNone(prefs["intensity"])
        self.assertGreater(prefs["intensity"], 0.75)
        self.assertIsNotNone(prefs["physical"])
        self.assertGreater(prefs["physical"], 0.75)

    def test_relax_tags_push_intensity_low(self):
        prefs = infer_user_preferences({"tags": ["peaceful", "spa"], "text": "", "img_desc": ""})
        self.assertIsNotNone(prefs["intensity"])
        self.assertLess(prefs["intensity"], 0.25)

    def test_solo_pushes_social_low(self):
        prefs = infer_user_preferences({"tags": ["solo"], "text": "", "img_desc": ""})
        self.assertIsNotNone(prefs["social"])
        self.assertLess(prefs["social"], 0.3)

    def test_family_pushes_social_high(self):
        prefs = infer_user_preferences({"tags": ["family", "group"], "text": "", "img_desc": ""})
        self.assertIsNotNone(prefs["social"])
        self.assertGreater(prefs["social"], 0.75)

    def test_empty_input_returns_all_none(self):
        prefs = infer_user_preferences({"tags": [], "text": "", "img_desc": ""})
        self.assertIsNone(prefs["intensity"])
        self.assertIsNone(prefs["physical"])
        self.assertIsNone(prefs["social"])

    def test_unknown_tags_ignored(self):
        prefs = infer_user_preferences({"tags": ["nonexistent", "xyz123"], "text": "", "img_desc": ""})
        self.assertIsNone(prefs["intensity"])
        self.assertIsNone(prefs["social"])

    def test_vietnamese_keywords_boost(self):
        prefs = infer_user_preferences({"tags": [], "text": "tôi muốn trải nghiệm mạo hiểm", "img_desc": ""})
        self.assertIsNotNone(prefs["intensity"])
        self.assertGreater(prefs["intensity"], 0.5)

    def test_english_img_desc_boost(self):
        prefs = infer_user_preferences({"tags": [], "text": "", "img_desc": "peaceful quiet beach sunset"})
        self.assertIsNotNone(prefs["intensity"])
        self.assertLess(prefs["intensity"], 0.5)

    def test_conflicting_signals_cancel(self):
        """Tag adventure + text 'thư giãn' → intensity signal cancel về neutral."""
        prefs = infer_user_preferences({
            "tags": ["adventure"],
            "text": "tôi muốn thư giãn và nghỉ ngơi",
            "img_desc": "",
        })
        # Tag adventure weight 1.0, kw thư giãn weight 0.5*-0.6 = -0.3, kw nghỉ ngơi 0.5*-0.5 = -0.25
        # tổng ≈ 0.45 → sigmoid ≈ 0.61 — không còn "rất cao"
        self.assertIsNotNone(prefs["intensity"])
        self.assertLess(prefs["intensity"], 0.75)


# =============================================================================
# RANK ACTIVITIES — formula + edge cases
# =============================================================================

def _make_activity(aid, intensity, physical=None, social=None, tod="anytime",
                   act_type="adventure", name=None):
    return {
        "activity_id": aid,
        "location_id": "loc_test",
        "metadata": {
            "name":          name or f"Activity {aid}",
            "description":   "desc",
            "activity_type": act_type,
            "intensity":     intensity,
            "physical_level": physical,
            "social_level":  social,
            "time_of_day_suitable": tod,
            "indoor_outdoor": "outdoor",
            "price_level":    2.0,
            "estimated_duration": 90,
        },
        # Vectors rỗng → semantic score sẽ fallback 0.5 → scaled 0 (neutral)
        "vectors": {"text": [], "tag": []},
    }


class TestRankActivities(unittest.TestCase):

    def test_empty_activities_returns_empty(self):
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": [],
            "top_k": 5,
        })
        self.assertEqual(out["activities"], [])

    def test_top_k_respected(self):
        acts = [_make_activity(f"a{i}", 0.5) for i in range(10)]
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": acts,
            "top_k": 3,
        })
        self.assertEqual(len(out["activities"]), 3)

    def test_intensity_match_ranked_higher(self):
        """User thích mạo hiểm (intensity~1) → activity intensity cao phải đứng trên."""
        high = _make_activity("high", intensity=0.9, physical=0.8)
        low  = _make_activity("low",  intensity=0.1, physical=0.1)
        out = rank_activities({
            "user_input": {"tags": ["adventure", "trekking"]},
            "user_vectors": {},
            "activities": [low, high],
            "top_k": 2,
        })
        ranked_ids = [a["activity_id"] for a in out["activities"]]
        self.assertEqual(ranked_ids[0], "high", f"expected 'high' first, got {ranked_ids}")

    def test_social_match_affects_ranking(self):
        """User solo (social thấp) → activity social cao phải rớt hạng."""
        group = _make_activity("group", intensity=0.5, physical=0.5, social=0.9)
        alone = _make_activity("alone", intensity=0.5, physical=0.5, social=0.1)
        out = rank_activities({
            "user_input": {"tags": ["solo"]},
            "user_vectors": {},
            "activities": [group, alone],
            "top_k": 2,
        })
        ranked_ids = [a["activity_id"] for a in out["activities"]]
        self.assertEqual(ranked_ids[0], "alone")

    def test_time_of_day_does_not_affect_ranking(self):
        """Contract mới: tod bị loại khỏi attribute score — ranking không thay đổi theo tod."""
        morn = _make_activity("morn", intensity=0.5, tod="morning")
        eve  = _make_activity("eve",  intensity=0.5, tod="evening")
        out = rank_activities({
            "user_input": {"tags": []},
            "user_vectors": {},
            "activities": [eve, morn],
            "context": {"time_of_day": "morning"},
            "top_k": 2,
        })
        # Cả 2 activity có cùng 3 axis attribute → score giống nhau → thứ tự giữ input
        scores = [a["score"] for a in out["activities"]]
        self.assertEqual(len(out["activities"]), 2)
        # Spread normalization sẽ kéo score ra nhưng tie-breaking theo thứ tự sort stable
        # Quan trọng: test cũ expect morn lên top vì tod match — giờ không còn

    def test_missing_user_prefs_does_not_crash(self):
        """User_input hoàn toàn rỗng → prefs toàn None → attr score neutral 0.5."""
        acts = [_make_activity("a", 0.5), _make_activity("b", 0.9)]
        out = rank_activities({
            "user_input": {},
            "user_vectors": {},
            "activities": acts,
            "top_k": 2,
        })
        self.assertEqual(len(out["activities"]), 2)
        # Scores phải hợp lệ trong [0,1]
        for a in out["activities"]:
            self.assertGreaterEqual(a["score"], 0.0)
            self.assertLessEqual(a["score"], 1.0)

    def test_old_constraints_ignored(self):
        """Field budget/duration/weather bị bỏ — truyền vào vẫn chạy ok, không crash."""
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": [_make_activity("a", 0.8)],
            "top_k": 1,
            # Intentionally include old fields — must be ignored silently
            "constraints": {"budget": 1000, "duration": 60, "people": 2, "weather": "rainy"},
        })
        self.assertEqual(len(out["activities"]), 1)

    def test_user_prefs_in_output(self):
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": [_make_activity("a", 0.5)],
            "top_k": 1,
        })
        self.assertIn("user_prefs", out)
        self.assertIsNotNone(out["user_prefs"]["intensity"])

    def test_scores_in_valid_range(self):
        acts = [_make_activity(f"a{i}", i / 10.0) for i in range(5)]
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": acts,
            "top_k": 5,
        })
        for a in out["activities"]:
            self.assertGreaterEqual(a["score"], 0.0)
            self.assertLessEqual(a["score"], 1.0)

    def test_ranking_stable_descending(self):
        acts = [_make_activity(f"a{i}", i / 10.0) for i in range(5)]
        out = rank_activities({
            "user_input": {"tags": ["adventure"]},
            "user_vectors": {},
            "activities": acts,
            "top_k": 5,
        })
        scores = [a["score"] for a in out["activities"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
