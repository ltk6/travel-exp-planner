"""
test_providers_and_cache.py — Unit tests for Đợt 1 + Đợt 2.

Chạy:
    python -m unittest backend.modules.n5_activity_generation.test.test_providers_and_cache -v

Test coverage:
  - Provider base: retry with backoff, RetryableError handling, non-retryable return None
  - Registry: get_provider, get_fallback_chain, dedupe, filter by availability
  - Cache: key stability (same input → same key), different input → different key,
           hit/miss counting, put ignores empty
  - Integration (mocked LLM): generate_from_llm sử dụng cache + fallback chain

Tất cả test đều mock HTTP — không gọi API thật, chạy nhanh (<1s tổng).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# ── Path setup ────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
_backend = os.path.join(_root, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from modules.n5_activity_generation.providers.base import LLMProvider, RetryableError
from modules.n5_activity_generation.providers import (
    GroqProvider, GeminiProvider, get_fallback_chain, get_provider,
)
from modules.n5_activity_generation import cache as llm_cache


# =============================================================================
# FAKE PROVIDER for base class tests (no HTTP)
# =============================================================================

class _FakeProvider(LLMProvider):
    """Provider giả để test base class retry/backoff logic."""
    name = "fake"
    model = "fake-1"
    rpm_limit = 60

    def __init__(self, api_key="fake-key", behavior=None):
        """
        behavior: list of ("ok"|"retryable"|"nonretryable", value_or_status).
        Base class gọi _call nhiều lần theo retry — lần thứ i dùng behavior[i].
        """
        self._key = api_key
        self._behavior = list(behavior or [])
        self._call_count = 0

    def _api_key(self):
        return self._key

    def _call(self, prompt, system=None, temperature=0.8, max_tokens=8192):
        idx = self._call_count
        self._call_count += 1
        if idx >= len(self._behavior):
            return None
        kind, val = self._behavior[idx]
        if kind == "ok":
            return val
        if kind == "retryable":
            raise RetryableError(f"fake {val}", status=val)
        if kind == "nonretryable":
            return None
        raise RuntimeError(f"unknown behavior: {kind}")


# =============================================================================
# BASE PROVIDER TESTS
# =============================================================================

class TestProviderBase(unittest.TestCase):

    def test_is_available_true_when_key_set(self):
        p = _FakeProvider(api_key="abc")
        self.assertTrue(p.is_available())

    def test_is_available_false_when_key_empty(self):
        for empty in ["", None, "   "]:
            p = _FakeProvider(api_key=empty)
            self.assertFalse(p.is_available(), f"empty={empty!r}")

    def test_generate_returns_none_if_unavailable(self):
        p = _FakeProvider(api_key=None, behavior=[("ok", "should not be reached")])
        self.assertIsNone(p.generate("prompt"))
        self.assertEqual(p._call_count, 0, "should not call when unavailable")

    def test_generate_success_first_try(self):
        p = _FakeProvider(behavior=[("ok", "RESULT")])
        self.assertEqual(p.generate("prompt", retries=2), "RESULT")
        self.assertEqual(p._call_count, 1)

    def test_generate_retries_then_succeeds(self):
        p = _FakeProvider(behavior=[
            ("retryable", 429),
            ("retryable", 503),
            ("ok", "LATE"),
        ])
        # Patch time.sleep để không phải chờ backoff thật
        with patch("modules.n5_activity_generation.providers.base.time.sleep"):
            result = p.generate("prompt", retries=2)
        self.assertEqual(result, "LATE")
        self.assertEqual(p._call_count, 3)

    def test_generate_gives_up_after_max_retries(self):
        p = _FakeProvider(behavior=[
            ("retryable", 429),
            ("retryable", 429),
            ("retryable", 429),
        ])
        with patch("modules.n5_activity_generation.providers.base.time.sleep"):
            result = p.generate("prompt", retries=2)
        self.assertIsNone(result)
        self.assertEqual(p._call_count, 3, "retries=2 means 3 total attempts")

    def test_nonretryable_returns_none_without_retry(self):
        """_call return None (vd 403 auth) — base không được retry."""
        p = _FakeProvider(behavior=[
            ("nonretryable", None),
            ("ok", "should not reach"),
        ])
        with patch("modules.n5_activity_generation.providers.base.time.sleep") as sleep:
            result = p.generate("prompt", retries=2)
        self.assertIsNone(result)
        self.assertEqual(p._call_count, 1)
        sleep.assert_not_called()


# =============================================================================
# REGISTRY TESTS
# =============================================================================

class TestRegistry(unittest.TestCase):

    def test_get_provider_returns_instance(self):
        p = get_provider("gemini")
        self.assertIsInstance(p, GeminiProvider)
        p = get_provider("groq")
        self.assertIsInstance(p, GroqProvider)

    def test_get_provider_unknown_returns_none(self):
        self.assertIsNone(get_provider("doesnotexist"))

    def test_fallback_chain_respects_primary_param(self):
        chain = get_fallback_chain(primary="groq", fallback="gemini")
        self.assertEqual(chain[0].name, "groq")
        self.assertEqual(chain[1].name, "gemini")

    def test_fallback_chain_dedupes_same_provider(self):
        chain = get_fallback_chain(primary="gemini", fallback="gemini,groq")
        names = [p.name for p in chain]
        self.assertEqual(names.count("gemini"), 1)

    def test_fallback_chain_filters_unavailable(self):
        """Provider không có API key bị loại khỏi chain."""
        with patch.object(GroqProvider, "_api_key", return_value=None):
            chain = get_fallback_chain(primary="groq", fallback="gemini")
            names = [p.name for p in chain]
            self.assertNotIn("groq", names)

    def test_fallback_chain_auto_fallback_when_empty(self):
        """LLM_FALLBACK rỗng → tự suy ra provider kia."""
        chain = get_fallback_chain(primary="gemini", fallback="")
        names = [p.name for p in chain]
        self.assertIn("groq", names, "empty fallback should auto-add groq")


# =============================================================================
# CACHE TESTS
# =============================================================================

class TestCache(unittest.TestCase):

    def setUp(self):
        llm_cache.clear()

    def _base_kwargs(self):
        return dict(
            location_name="Ha Long",
            location_tags=["beach", "island"],
            user_tags=["adventure"],
            user_text="muon mao hiem",
            budget_per_activity=500_000,
            max_time_per_activity=240,
            num_activities=10,
            schema_v2=True,
        )

    def test_key_is_deterministic(self):
        k1 = llm_cache.make_key(**self._base_kwargs())
        k2 = llm_cache.make_key(**self._base_kwargs())
        self.assertEqual(k1, k2)

    def test_key_insensitive_to_tag_order(self):
        a = self._base_kwargs()
        b = dict(a, user_tags=["adventure"], location_tags=["island", "beach"])
        self.assertEqual(
            llm_cache.make_key(**a),
            llm_cache.make_key(**b),
        )

    def test_key_insensitive_to_case_and_whitespace(self):
        a = self._base_kwargs()
        b = dict(a, location_name="  ha long  ", user_text="MUON MAO HIEM")
        self.assertEqual(
            llm_cache.make_key(**a),
            llm_cache.make_key(**b),
        )

    def test_key_changes_with_location(self):
        a = self._base_kwargs()
        b = dict(a, location_name="Sapa")
        self.assertNotEqual(
            llm_cache.make_key(**a),
            llm_cache.make_key(**b),
        )

    def test_key_changes_with_user_tags(self):
        a = self._base_kwargs()
        b = dict(a, user_tags=["relax"])
        self.assertNotEqual(
            llm_cache.make_key(**a),
            llm_cache.make_key(**b),
        )

    def test_key_changes_with_budget(self):
        a = self._base_kwargs()
        b = dict(a, budget_per_activity=1_000_000)
        self.assertNotEqual(
            llm_cache.make_key(**a),
            llm_cache.make_key(**b),
        )

    def test_key_changes_with_provider_env(self):
        k1 = llm_cache.make_key(**self._base_kwargs())
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq"}):
            k2 = llm_cache.make_key(**self._base_kwargs())
        self.assertNotEqual(k1, k2, "changing provider must invalidate cache")

    def test_put_get_roundtrip(self):
        key = llm_cache.make_key(**self._base_kwargs())
        data = [{"name": "act1"}, {"name": "act2"}]
        llm_cache.put(key, data)
        self.assertEqual(llm_cache.get(key), data)

    def test_put_ignores_empty(self):
        key = llm_cache.make_key(**self._base_kwargs())
        llm_cache.put(key, [])
        self.assertIsNone(llm_cache.get(key))
        self.assertEqual(llm_cache.stats()["stores"], 0)

    def test_stats_track_hits_and_misses(self):
        key = llm_cache.make_key(**self._base_kwargs())
        llm_cache.get(key)                        # miss
        llm_cache.put(key, [{"x": 1}])
        llm_cache.get(key)                        # hit
        llm_cache.get(key)                        # hit
        s = llm_cache.stats()
        self.assertEqual(s["hits"], 2)
        self.assertEqual(s["misses"], 1)
        self.assertAlmostEqual(s["hit_rate"], 2/3, places=2)


# =============================================================================
# INTEGRATION TESTS (generate_from_llm with mocked chain)
# =============================================================================

# Response tối thiểu hợp lệ cho validator (schema v2)
_FAKE_LLM_RESPONSE = """[
  {"activity_id":"a1","location_id":"loc_x","name":"Leo nui","description":"Trekking fun",
   "tags":["trekking","adventure"],"cost":100000,"estimated_duration":120,
   "best_time":["morning"],"suitable_for":["friends"],"difficulty":"medium","season":["jan"],
   "reason_template":"fits {matching_tags}"},
  {"activity_id":"a2","location_id":"loc_x","name":"An hai san","description":"Food fun",
   "tags":["food","seafood"],"cost":200000,"estimated_duration":60,
   "best_time":["evening"],"suitable_for":["couple"],"difficulty":"easy","season":["jan"],
   "reason_template":"fits {matching_tags}"}
]"""


class TestGenerateFromLLMWithCache(unittest.TestCase):

    def setUp(self):
        llm_cache.clear()

    def test_cache_hit_avoids_second_llm_call(self):
        """Gọi 2 lần cùng params — lần 2 không được gọi LLM."""
        from modules.n5_activity_generation.n5_llm_generator import generate_from_llm

        fake = _FakeProvider(behavior=[("ok", _FAKE_LLM_RESPONSE)])
        with patch(
            "modules.n5_activity_generation.n5_llm_generator.get_fallback_chain",
            return_value=[fake],
        ):
            kwargs = dict(
                location_name="Test Loc",
                location_description="desc",
                location_tags=["beach"],
                user_tags=["adventure"],
                budget_per_activity=500_000,
                max_time_per_activity=240,
                num_activities=2,
                schema_v2=True,
                user_text="test",
            )
            r1 = generate_from_llm(**kwargs)
            r2 = generate_from_llm(**kwargs)

        self.assertEqual(len(r1), 2)
        self.assertEqual(len(r2), 2)
        self.assertEqual(fake._call_count, 1, "cache hit must skip 2nd LLM call")
        self.assertEqual(llm_cache.stats()["hits"], 1)
        self.assertEqual(llm_cache.stats()["misses"], 1)

    def test_fallback_chain_switches_on_primary_fail(self):
        """Provider đầu fail (retryable cạn retry) → chain chuyển provider 2."""
        from modules.n5_activity_generation.n5_llm_generator import generate_from_llm

        primary = _FakeProvider(behavior=[
            ("retryable", 429), ("retryable", 429), ("retryable", 429),
        ])
        secondary = _FakeProvider(behavior=[("ok", _FAKE_LLM_RESPONSE)])

        with patch(
            "modules.n5_activity_generation.n5_llm_generator.get_fallback_chain",
            return_value=[primary, secondary],
        ), patch("modules.n5_activity_generation.providers.base.time.sleep"):
            result = generate_from_llm(
                location_name="Test Loc",
                location_description="desc",
                location_tags=[],
                user_tags=[],
                budget_per_activity=500_000,
                max_time_per_activity=240,
                num_activities=2,
                schema_v2=True,
                user_text="",
            )

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(primary._call_count, 3, "primary exhausts retries")
        self.assertEqual(secondary._call_count, 1, "secondary answers on first try")

    def test_all_providers_fail_returns_none(self):
        from modules.n5_activity_generation.n5_llm_generator import generate_from_llm

        p1 = _FakeProvider(behavior=[("retryable", 500)] * 3)
        p2 = _FakeProvider(behavior=[("retryable", 500)] * 3)

        with patch(
            "modules.n5_activity_generation.n5_llm_generator.get_fallback_chain",
            return_value=[p1, p2],
        ), patch("modules.n5_activity_generation.providers.base.time.sleep"):
            result = generate_from_llm(
                location_name="X",
                location_description="",
                location_tags=[],
                user_tags=[],
                budget_per_activity=1,
                max_time_per_activity=1,
                num_activities=1,
                schema_v2=True,
                user_text="",
            )
        self.assertIsNone(result)
        self.assertEqual(llm_cache.stats()["stores"], 0, "no cache on failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
