"""
N8 Orchestrator - Module Bench Test
Benchmarks orchestration overhead, cache behavior, and endpoint routing with
mocked downstream modules so results reflect N8 itself instead of model/API latency.
Outputs bench_n8_results.json and bench_n8.md.
"""
from __future__ import annotations

import base64
import copy
import json
import os
import shutil
import sys
import time
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import INTERNAL_API_KEY

BASE_DIR = Path(__file__).resolve().parent
CACHE_ROOT = BASE_DIR / "_n8_bench_cache"

STATE: dict[str, int | str] = {
    "fingerprint": "fp_v1",
    "db_fetches": 0,
    "fingerprint_calls": 0,
    "embed_calls": 0,
    "embed_batch_calls": 0,
    "n2_calls": 0,
    "rank_location_calls": 0,
    "n5_calls": 0,
    "rank_activity_calls": 0,
    "feedback_calls": 0,
}

IMAGE_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(b"fake-jpeg-binary").decode("ascii")

FAKE_LOCATIONS = [
    {
        "location_id": "loc_beach",
        "vectors": {
            "text": [1.0, 0.0, 0.0],
            "aug_text": [1.0, 0.0, 0.0],
            "aug_tags": [1.0, 0.0, 0.0],
            "img_desc": [1.0, 0.0, 0.0],
        },
        "metadata": {
            "name": "Bai Sao Phu Quoc",
            "description": "Beach destination",
            "tags": ["beach", "relax"],
        },
        "geo": {"lat": 10.0, "lng": 104.0},
        "images": [IMAGE_DATA_URI],
    },
    {
        "location_id": "loc_city",
        "vectors": {
            "text": [0.8, 0.1, 0.0],
            "aug_text": [0.8, 0.1, 0.0],
            "aug_tags": [0.8, 0.1, 0.0],
            "img_desc": [0.8, 0.1, 0.0],
        },
        "metadata": {
            "name": "Hoi An Old Town",
            "description": "Culture destination",
            "tags": ["culture", "food"],
        },
        "geo": {"lat": 15.8, "lng": 108.3},
        "images": [IMAGE_DATA_URI],
    },
    {
        "location_id": "loc_mountain",
        "vectors": {
            "text": [0.6, 0.2, 0.0],
            "aug_text": [0.6, 0.2, 0.0],
            "aug_tags": [0.6, 0.2, 0.0],
            "img_desc": [0.6, 0.2, 0.0],
        },
        "metadata": {
            "name": "Fansipan",
            "description": "Mountain destination",
            "tags": ["mountain", "adventure"],
        },
        "geo": {"lat": 22.3, "lng": 103.8},
        "images": [IMAGE_DATA_URI],
    },
]


def _deepcopy_locations() -> list[dict]:
    return copy.deepcopy(FAKE_LOCATIONS)


def _register_module(name: str, module: types.ModuleType) -> None:
    sys.modules[name] = module


def _install_fake_dependencies() -> None:
    modules_pkg = types.ModuleType("modules")
    modules_pkg.__path__ = []
    _register_module("modules", modules_pkg)

    shared_pkg = types.ModuleType("shared")
    shared_pkg.__path__ = []
    _register_module("shared", shared_pkg)

    shared_weights = types.ModuleType("shared.weights")
    shared_weights.get_weights = lambda text_k, tags_k: {
        "text": 0.55,
        "aug_text": 0.15,
        "aug_tags": 0.20,
        "img_desc": 0.10,
        "text_k": text_k,
        "tags_k": tags_k,
    }
    _register_module("shared.weights", shared_weights)
    shared_pkg.weights = shared_weights

    n3_pkg = types.ModuleType("n3_database")
    n3_pkg.__path__ = []

    def fake_get_all_locations(include_images: bool = True) -> dict:
        STATE["db_fetches"] += 1
        locations = _deepcopy_locations()
        if not include_images:
            for loc in locations:
                loc["images"] = []
        return {
            "status": "success",
            "total": len(locations),
            "data": locations,
            "metadata": {"source": "fake_n3", "latency_ms": 4},
        }

    n3_pkg.get_all_locations = fake_get_all_locations
    _register_module("n3_database", n3_pkg)

    n3_db_manager = types.ModuleType("n3_database.db_manager")

    class _DummyConn:
        def close(self) -> None:
            return None

    def fake_get_db_fingerprint() -> str:
        STATE["fingerprint_calls"] += 1
        return str(STATE["fingerprint"])

    n3_db_manager.get_db_fingerprint = fake_get_db_fingerprint
    n3_db_manager._get_connection = lambda: _DummyConn()
    _register_module("n3_database.db_manager", n3_db_manager)
    n3_pkg.db_manager = n3_db_manager

    n1_pkg = types.ModuleType("modules.n1_embedding")
    n1_pkg.__path__ = []

    def fake_embed(data) -> dict:
        STATE["embed_calls"] += 1
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump()
        elif isinstance(data, dict):
            data_dict = data
        else:
            data_dict = getattr(data, "__dict__", {})
        text = data_dict.get("text", "")
        tags = data_dict.get("tags", [])
        img_desc = data_dict.get("img_desc", "")
        return {
            "text_k": min(len(text.split()), 4),
            "tags_k": len(tags),
            "preprocessed": {"text": text, "aug_text": text, "aug_tags": " ".join(tags), "img_desc": img_desc},
            "vectors": {
                "text": [1.0, 0.0, 0.0],
                "aug_text": [1.0, 0.0, 0.0],
                "aug_tags": [0.9, 0.1, 0.0],
                "img_desc": [0.8, 0.2, 0.0] if img_desc else None,
            },
            "metadata": {"model": "fake-embedder", "device": "cpu", "latency_ms": 1},
        }

    def fake_embed_batch(data_list: list) -> list[dict]:
        STATE["embed_batch_calls"] += 1
        results = []
        for item in data_list:
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif isinstance(item, dict):
                item_dict = item
            else:
                item_dict = getattr(item, "__dict__", {})
            results.append({
                "text_k": min(len(item_dict.get("text", "").split()), 4),
                "tags_k": len(item_dict.get("tags", [])),
                "preprocessed": item_dict,
                "vectors": {
                    "text": [0.7, 0.1, 0.0],
                    "aug_text": [0.7, 0.1, 0.0],
                    "aug_tags": [0.6, 0.2, 0.0],
                    "img_desc": [0.5, 0.3, 0.0],
                },
                "metadata": {"model": "fake-embedder", "device": "cpu", "latency_ms": 1},
            })
        return results

    n1_pkg.embed = fake_embed
    n1_pkg.embed_batch = fake_embed_batch
    _register_module("modules.n1_embedding", n1_pkg)
    modules_pkg.n1_embedding = n1_pkg

    n1_embedder = types.ModuleType("modules.n1_embedding.embedder")
    n1_embedder.get_model = lambda: SimpleNamespace(device="cpu")
    _register_module("modules.n1_embedding.embedder", n1_embedder)
    n1_pkg.embedder = n1_embedder

    alt_n1_pkg = types.ModuleType("modules.alt_n1_embedding")
    alt_n1_pkg.__path__ = []

    def fake_alt_embed(data, is_query: bool = False) -> dict:
        STATE["embed_calls"] += 1
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump()
        elif isinstance(data, dict):
            data_dict = data
        else:
            data_dict = getattr(data, "__dict__", {})
        text = data_dict.get("text", "")
        tags = data_dict.get("tags", [])
        img_desc = data_dict.get("img_desc", "")
        return {
            "text_k": min(len(text.split()), 4),
            "tags_k": len(tags),
            "preprocessed": {"text": text, "aug_text": text, "aug_tags": " ".join(tags), "img_desc": img_desc},
            "vectors": {
                "text": [1.0, 0.0, 0.0],
                "aug_text": [1.0, 0.0, 0.0],
                "aug_tags": [0.9, 0.1, 0.0],
                "img_desc": [0.8, 0.2, 0.0] if img_desc else None,
            },
            "metadata": {"model": "fake-alt-embedder", "device": "cpu", "latency_ms": 1},
        }

    def fake_alt_embed_batch(data_list: list, is_query: bool = False) -> list[dict]:
        STATE["embed_batch_calls"] += 1
        results = []
        for item in data_list:
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump()
            elif isinstance(item, dict):
                item_dict = item
            else:
                item_dict = getattr(item, "__dict__", {})
            results.append({
                "text_k": min(len(item_dict.get("text", "").split()), 4),
                "tags_k": len(item_dict.get("tags", [])),
                "preprocessed": item_dict,
                "vectors": {
                    "text": [0.7, 0.1, 0.0],
                    "aug_text": [0.7, 0.1, 0.0],
                    "aug_tags": [0.6, 0.2, 0.0],
                    "img_desc": [0.5, 0.3, 0.0],
                },
                "metadata": {"model": "fake-alt-embedder", "device": "cpu", "latency_ms": 1},
            })
        return results

    alt_n1_pkg.embed = fake_alt_embed
    alt_n1_pkg.embed_batch = fake_alt_embed_batch
    _register_module("modules.alt_n1_embedding", alt_n1_pkg)
    modules_pkg.alt_n1_embedding = alt_n1_pkg

    alt_n1_embedder = types.ModuleType("modules.alt_n1_embedding.embedder")
    alt_n1_embedder.get_model = lambda: SimpleNamespace(device="cpu")
    _register_module("modules.alt_n1_embedding.embedder", alt_n1_embedder)
    alt_n1_pkg.embedder = alt_n1_embedder

    n2_pkg = types.ModuleType("modules.n2_image_processing")
    n2_pkg.__path__ = []

    def fake_process_image(data) -> dict:
        STATE["n2_calls"] += 1
        return {
            "img_desc": "sunny beach with calm sea",
            "metadata": {"model": "fake-vision", "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        }

    n2_pkg.process_image = fake_process_image
    _register_module("modules.n2_image_processing", n2_pkg)
    modules_pkg.n2_image_processing = n2_pkg

    n4_pkg = types.ModuleType("modules.n4_location_ranking")

    def fake_rank_locations(payload) -> dict:
        STATE["rank_location_calls"] += 1
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = getattr(payload, "__dict__", {})
        top_k = int(payload_dict.get("top_k", len(payload_dict.get("locations", []))))
        ranked = []
        for idx, loc in enumerate(payload_dict.get("locations", [])[:top_k]):
            ranked.append({
                "location_id": loc.get("location_id"),
                "score": round(1.0 - idx * 0.1, 2),
                "reason": f"mock_rank_{idx + 1}",
            })
        return {
            "locations": ranked,
            "metadata": {"latency_ms": 2, "weights": {"text": 0.55, "aug_tags": 0.20}},
        }

    n4_pkg.rank_locations = fake_rank_locations
    _register_module("modules.n4_location_ranking", n4_pkg)
    modules_pkg.n4_location_ranking = n4_pkg

    n5_pkg = types.ModuleType("modules.n5_activity_generation")
    n5_pkg.__path__ = []
    _register_module("modules.n5_activity_generation", n5_pkg)
    modules_pkg.n5_activity_generation = n5_pkg

    n5_generator = types.ModuleType("modules.n5_activity_generation.n5_activity_generator")

    def fake_generate_activities(payload) -> dict:
        STATE["n5_calls"] += 1
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = getattr(payload, "__dict__", {})
        locations = payload_dict.get("locations", [])
        location = locations[0] if locations else {}
        location_id = location.get("location_id", "loc_unknown")
        activities = []
        for idx in range(3):
            activities.append({
                "activity_id": f"{location_id}_act_{idx + 1}",
                "location_id": location_id,
                "metadata": {
                    "name": f"Activity {idx + 1}",
                    "description": f"Mock activity {idx + 1}",
                    "tags": ["mock", "relax"],
                    "activity_type": "relaxation" if idx == 0 else "exploration",
                    "intensity": 0.2 + idx * 0.2,
                    "physical_level": 0.1 + idx * 0.2,
                    "social_level": 0.3 + idx * 0.1,
                },
            })
        return {
            "activities": activities,
            "metadata": {
                "latency_ms": 6,
                "per_location": [{
                    "location_id": location_id,
                    "provider_used": "mock_provider",
                    "model_used": "mock_llm",
                    "latency_ms": 6,
                    "usage": {"prompt_tokens": 20, "completion_tokens": 15},
                }],
            },
        }

    n5_generator.generate_activities = fake_generate_activities
    _register_module("modules.n5_activity_generation.n5_activity_generator", n5_generator)
    n5_pkg.n5_activity_generator = n5_generator

    n5_providers = types.ModuleType("modules.n5_activity_generation.providers")
    n5_providers.get_llm_chain = lambda: [
        SimpleNamespace(name="primary", model="mock_llm", rpm_limit=30),
        SimpleNamespace(name="fallback", model="mock_fallback", rpm_limit=60),
    ]
    _register_module("modules.n5_activity_generation.providers", n5_providers)
    n5_pkg.providers = n5_providers

    n6_pkg = types.ModuleType("modules.n6_activity_ranking")
    n6_pkg.__path__ = []
    _register_module("modules.n6_activity_ranking", n6_pkg)
    modules_pkg.n6_activity_ranking = n6_pkg

    n6_rank = types.ModuleType("modules.n6_activity_ranking.rank_activities")

    def fake_rank_activities(payload) -> dict:
        STATE["rank_activity_calls"] += 1
        if hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump()
        elif isinstance(payload, dict):
            payload_dict = payload
        else:
            payload_dict = getattr(payload, "__dict__", {})
        top_k = int(payload_dict.get("top_k", len(payload_dict.get("activities", []))))
        ranked = []
        for idx, act in enumerate(payload_dict.get("activities", [])[:top_k]):
            ranked.append({
                "activity_id": act.get("activity_id"),
                "location_id": act.get("location_id"),
                "score": round(0.95 - idx * 0.08, 2),
                "reason": f"mock_activity_rank_{idx + 1}",
            })
        return {
            "activities": ranked,
            "metadata": {
                "latency_ms": 3,
                "user_prefs": {"intensity": 0.3, "physical": 0.2, "social": 0.4},
            },
        }

    n6_rank.rank_activities = fake_rank_activities
    _register_module("modules.n6_activity_ranking.rank_activities", n6_rank)
    n6_pkg.rank_activities = n6_rank

    n17_pkg = types.ModuleType("modules.n17_feedback_processing")

    def fake_process_feedback(user_input, user_tags=None, img_desc="", feedback_text="", llm_chain=None) -> dict:
        STATE["feedback_calls"] += 1
        if hasattr(user_input, "model_dump") or isinstance(user_input, dict):
            val = user_input.model_dump() if hasattr(user_input, "model_dump") else user_input
            u_input = val.get("user_input", "")
            u_tags = val.get("user_tags") or []
            u_img = val.get("img_desc") or ""
            f_text = val.get("feedback_text", "")
        else:
            u_input = user_input
            u_tags = user_tags or []
            u_img = img_desc
            f_text = feedback_text

        return {
            "refined_text": f"{u_input} | refined: {f_text}",
            "refined_tags": list(dict.fromkeys((u_tags or []) + ["refined"])),
            "refined_img_desc": u_img or "refined image intent",
            "explanation": "Mock refinement applied.",
            "metadata": {"model": "mock_feedback", "provider": "mock_provider", "usage": {"prompt_tokens": 12, "completion_tokens": 8}},
        }

    n17_pkg.process_feedback = fake_process_feedback
    _register_module("modules.n17_feedback_processing", n17_pkg)
    modules_pkg.n17_feedback_processing = n17_pkg

    activity_retrievals_pkg = types.ModuleType("modules.activity_retrievals")
    activity_retrievals_pkg.__path__ = []
    _register_module("modules.activity_retrievals", activity_retrievals_pkg)
    modules_pkg.activity_retrievals = activity_retrievals_pkg

    ar_normalizers = types.ModuleType("modules.activity_retrievals.normalizers")
    ar_normalizers.__path__ = []
    _register_module("modules.activity_retrievals.normalizers", ar_normalizers)
    activity_retrievals_pkg.normalizers = ar_normalizers

    ar_llm = types.ModuleType("modules.activity_retrievals.normalizers.llm")
    ar_llm.normalize_all = lambda activities, ctx: activities
    _register_module("modules.activity_retrievals.normalizers.llm", ar_llm)
    ar_normalizers.llm = ar_llm

    ar_processor = types.ModuleType("modules.activity_retrievals.processor")
    ar_processor._drop_anchor_duplicates = lambda activities, loc_name: activities
    _register_module("modules.activity_retrievals.processor", ar_processor)
    activity_retrievals_pkg.processor = ar_processor


def _prepare_n8_runtime():
    _install_fake_dependencies()
    from backend.n8_orchestrator.app import app
    from backend.n8_orchestrator import services as n8_services

    if CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)
    (CACHE_ROOT / "image_cache").mkdir(parents=True, exist_ok=True)

    n8_services.CACHE_DIR = str(CACHE_ROOT)
    n8_services.CACHE_FILE = str(CACHE_ROOT / "location_cache.json")
    n8_services.IMG_CACHE_DIR = str(CACHE_ROOT / "image_cache")
    n8_services._CACHED_LOCATIONS_DATA = None
    n8_services._CACHED_FINGERPRINT = None
    app.testing = True
    return app, n8_services


def _reset_state_counters() -> None:
    for key in [
        "db_fetches",
        "fingerprint_calls",
        "embed_calls",
        "embed_batch_calls",
        "n2_calls",
        "rank_location_calls",
        "n5_calls",
        "rank_activity_calls",
        "feedback_calls",
    ]:
        STATE[key] = 0


def _snapshot_counts() -> dict[str, int]:
    return {
        "db_fetches": int(STATE["db_fetches"]),
        "fingerprint_calls": int(STATE["fingerprint_calls"]),
        "embed_calls": int(STATE["embed_calls"]),
        "embed_batch_calls": int(STATE["embed_batch_calls"]),
        "n2_calls": int(STATE["n2_calls"]),
        "rank_location_calls": int(STATE["rank_location_calls"]),
        "n5_calls": int(STATE["n5_calls"]),
        "rank_activity_calls": int(STATE["rank_activity_calls"]),
        "feedback_calls": int(STATE["feedback_calls"]),
    }


def _delta_counts(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {k: after[k] - before[k] for k in before}


def _reset_cache_storage(n8_services) -> None:
    n8_services._CACHED_LOCATIONS_DATA = None
    n8_services._CACHED_FINGERPRINT = None
    if CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)
    (CACHE_ROOT / "image_cache").mkdir(parents=True, exist_ok=True)


def bench_cache(n8_services) -> dict:
    _reset_state_counters()
    _reset_cache_storage(n8_services)

    stages: list[dict] = []

    def record_stage(name: str, func, expected_fetches: int) -> None:
        before_fetches = int(STATE["db_fetches"])
        t0 = time.perf_counter()
        data = func()
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        after_fetches = int(STATE["db_fetches"])
        ok = after_fetches == expected_fetches and len(data) == len(FAKE_LOCATIONS)
        stages.append({
            "name": name,
            "latency_ms": elapsed_ms,
            "db_fetches_before": before_fetches,
            "db_fetches_after": after_fetches,
            "count": len(data),
            "status": "PASS" if ok else "FAIL",
        })
        print(f"  [cache:{name:<12}] {elapsed_ms:4d}ms  {'PASS' if ok else 'FAIL'}  db={after_fetches}")

    record_stage("cold_fetch", lambda: n8_services.get_all_locations_cached(), 1)
    record_stage("warm_ram", lambda: n8_services.get_all_locations_cached(), 1)

    n8_services._CACHED_LOCATIONS_DATA = None
    n8_services._CACHED_FINGERPRINT = None
    record_stage("warm_disk", lambda: n8_services.get_all_locations_cached(), 1)
    record_stage("force_refresh", lambda: n8_services.get_all_locations_cached(force_refresh=True), 2)

    cache_file_exists = os.path.exists(n8_services.CACHE_FILE)
    image_files = list(Path(n8_services.IMG_CACHE_DIR).glob("*.jpg"))
    overall_pass = all(stage["status"] == "PASS" for stage in stages) and cache_file_exists

    return {
        "status": "PASS" if overall_pass else "FAIL",
        "stages": stages,
        "cache_file_exists": cache_file_exists,
        "image_cache_files": len(image_files),
    }


def _request(client, method: str, path: str, payload: dict | None = None, protected: bool = False) -> tuple[dict, int]:
    headers = {}
    if protected:
        headers["X-Internal-Key"] = INTERNAL_API_KEY
    t0 = time.perf_counter()
    if method == "GET":
        response = client.get(path, headers=headers)
    else:
        response = client.post(path, json=payload or {}, headers=headers)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return response.get_json() or {}, elapsed_ms, response.status_code


def bench_endpoints(app, n8_services) -> list[dict]:
    client = app.test_client()
    results: list[dict] = []

    def add_result(name: str, method: str, path: str, payload: dict | None, protected: bool, validator) -> None:
        before = _snapshot_counts()
        body, elapsed_ms, status_code = _request(client, method, path, payload, protected)
        after = _snapshot_counts()
        deltas = _delta_counts(before, after)
        ok, note = validator(body, status_code, deltas)
        results.append({
            "name": name,
            "method": method,
            "path": path,
            "latency_ms": elapsed_ms,
            "status_code": status_code,
            "status": "PASS" if ok else "FAIL",
            "note": note,
            "module_deltas": deltas,
        })
        print(f"  [api:{name:<18}] {elapsed_ms:4d}ms  {'PASS' if ok else 'FAIL'}  {status_code}")

    _reset_state_counters()
    _reset_cache_storage(n8_services)

    add_result(
        "health",
        "GET",
        "/health",
        None,
        False,
        lambda body, code, deltas: (
            code == 200 and body.get("status") == "ok" and isinstance(body.get("llm_chain"), list),
            "health ok",
        ),
    )

    add_result(
        "fingerprint",
        "GET",
        "/cache/fingerprint",
        None,
        False,
        lambda body, code, deltas: (
            code == 200 and body.get("fingerprint") == STATE["fingerprint"] and deltas["fingerprint_calls"] >= 1,
            "fingerprint route",
        ),
    )

    recommend_payload = {
        "text": "need a relaxing beach trip",
        "tags": ["beach", "relax"],
        "top_k_locations": 2,
        "top_k_activities": 2,
    }
    add_result(
        "recommend_cold",
        "POST",
        "/recommend",
        recommend_payload,
        True,
        lambda body, code, deltas: (
            code == 200
            and len(body.get("locations", [])) == 2
            and deltas["db_fetches"] == 1
            and deltas["embed_calls"] == 1
            and deltas["rank_location_calls"] == 1,
            "cold cache recommend",
        ),
    )

    add_result(
        "recommend_warm",
        "POST",
        "/recommend",
        recommend_payload,
        True,
        lambda body, code, deltas: (
            code == 200
            and len(body.get("locations", [])) == 2
            and deltas["db_fetches"] == 0
            and deltas["embed_calls"] == 1
            and deltas["rank_location_calls"] == 1,
            "warm cache recommend",
        ),
    )

    activity_payload = {
        "text": "need a relaxing beach trip",
        "tags": ["beach", "relax"],
        "img_desc": "",
        "text_k": 3,
        "tags_k": 2,
        "user_vectors": {
            "text": [1.0, 0.0, 0.0],
            "aug_text": [1.0, 0.0, 0.0],
            "aug_tags": [0.9, 0.1, 0.0],
            "img_desc": [],
        },
        "location": {
            "location_id": "loc_beach",
            "metadata": {"name": "Bai Sao Phu Quoc", "description": "Beach destination"},
        },
        "top_k_activities": 2,
    }
    add_result(
        "activities",
        "POST",
        "/activities",
        activity_payload,
        True,
        lambda body, code, deltas: (
            code == 200
            and body.get("status") == "success"
            and len(body.get("activities", [])) == 2
            and deltas["n5_calls"] == 1
            and deltas["embed_batch_calls"] == 1
            and deltas["rank_activity_calls"] == 1,
            "activities pipeline",
        ),
    )

    feedback_recommend_payload = {
        "text": "need a relaxing beach trip",
        "tags": ["beach", "relax"],
        "feedback": "make it more culture-friendly",
        "top_k_locations": 2,
    }
    add_result(
        "feedback_recommend",
        "POST",
        "/feedback/recommend",
        feedback_recommend_payload,
        False,
        lambda body, code, deltas: (
            code == 200
            and "refined" in body
            and deltas["feedback_calls"] == 1
            and deltas["embed_calls"] == 1
            and deltas["rank_location_calls"] == 1,
            "recommend feedback loop",
        ),
    )

    feedback_activities_payload = {
        "text": "need a relaxing beach trip",
        "tags": ["beach", "relax"],
        "feedback": "make activities more active",
        "text_k": 3,
        "tags_k": 2,
        "user_vectors": {
            "text": [1.0, 0.0, 0.0],
            "aug_text": [1.0, 0.0, 0.0],
            "aug_tags": [0.9, 0.1, 0.0],
            "img_desc": [],
        },
        "location": {
            "location_id": "loc_beach",
            "metadata": {"name": "Bai Sao Phu Quoc", "description": "Beach destination"},
        },
        "top_k_activities": 2,
    }
    add_result(
        "feedback_activities",
        "POST",
        "/feedback/activities",
        feedback_activities_payload,
        False,
        lambda body, code, deltas: (
            code == 200
            and "refined" in body
            and len(body.get("activities", [])) == 2
            and deltas["feedback_calls"] == 1
            and deltas["n5_calls"] == 1
            and deltas["embed_batch_calls"] == 1
            and deltas["rank_activity_calls"] == 1,
            "activities feedback loop",
        ),
    )

    add_result(
        "cache_reset",
        "POST",
        "/cache/reset",
        {},
        False,
        lambda body, code, deltas: (
            code == 200 and body.get("status") == "success" and deltas["db_fetches"] == 1,
            "manual cache refresh",
        ),
    )

    return results


def _build_markdown(output: dict, date_str: str) -> str:
    cache = output["cache"]
    endpoints = output["endpoints"]
    passed_endpoints = sum(1 for item in endpoints if item["status"] == "PASS")

    lines: list[str] = []

    def line(text: str = "") -> None:
        lines.append(text)

    line("# N8 - Module Orchestrator: Báo Cáo Bench Test\n")
    line(f"**Ngày:** {date_str}  ")
    line("**Chế độ bench:** Mocked downstream modules (N1, N2, N3, N4, N5, N6, N17) để đo dung lượng overhead của N8  ")
    line("**Mục tiêu:** Cache behavior, service orchestration, endpoint routing, feedback loop  ")
    line()
    line("---")
    line()
    line("## 1. Tổng Quan Module\n")
    line("N8 là lớp điều phối trung tâm của hệ thống. Giá trị cần bench ở đây không nằm ở chất lượng model mà nằm ở việc:")
    line("- Gọi đúng module theo thứ tự pipeline")
    line("- Giảm latency bằng hybrid cache")
    line("- Duy trì contract JSON ổn định cho frontend")
    line("- Hỗ trợ feedback loop mà không bắt frontend tự xử lý logic refine")
    line()
    line("Bài bench này mock toàn bộ module bên dưới để loại bỏ noise từ embedding, database thật, và LLM API.")
    line()
    line("---")
    line()
    line("## 2. Cache Benchmark\n")
    line("| Giai đoạn | Latency (ms) | DB fetch trước | DB fetch sau | Bản ghi | Trạng thái |")
    line("|-----------|:------------:|:--------------:|:------------:|:-------:|:---------:|")
    for stage in cache["stages"]:
        line(
            f"| {stage['name']} | {stage['latency_ms']} | {stage['db_fetches_before']} | "
            f"{stage['db_fetches_after']} | {stage['count']} | {stage['status']} |"
        )
    line()
    line(f"- Cache file tạo thành công: **{cache['cache_file_exists']}**")
    line(f"- Số file ảnh cache tạo được: **{cache['image_cache_files']}**")
    line(f"- Kết quả tổng: **{cache['status']}**")
    line()
    line("---")
    line()
    line("## 3. Endpoint Benchmark\n")
    line("| Test | Route | Code | Latency (ms) | Status | Module deltas |")
    line("|------|-------|:----:|:------------:|:------:|---------------|")
    for item in endpoints:
        line(
            f"| {item['name']} | `{item['method']} {item['path']}` | {item['status_code']} | "
            f"{item['latency_ms']} | {item['status']} | `{item['module_deltas']}` |"
        )
    line()
    line(f"**Pass endpoint tests:** {passed_endpoints}/{len(endpoints)}")
    line()
    line("---")
    line()
    line("## 4. Nhận Xét Chính\n")
    line("1. **Hybrid cache hoạt động đúng đường đi:** Lần đầu gọi N3, lần sau hit RAM, xóa RAM thì hit Disk, force refresh mới gọi lại N3.")
    line("2. **Recommend pipeline của N8 gọn và đúng hợp đồng:** 1 lần embed + 1 lần rank_locations, trong khi warm cache không phát sinh thêm DB fetch.")
    line("3. **Activities pipeline hợp lý cho presentation:** N8 thực sự là cầu nối N5 -> N1 batch -> N6, thay vì chỉ là một route wrapper mỏng.")
    line("4. **Feedback loop có giá trị kiến trúc rõ ràng:** Feedback routes kích hoạt N17 rồi chạy lại workflow chính, giữ response shape ổn định cho UI.")
    line("5. **Bench này đo đúng N8:** Vì downstream đã được mock, các con số latency ở đây phản ánh orchestration overhead và cache behavior thay vì model latency.")

    return "\n".join(lines)


def main() -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    app, n8_services = _prepare_n8_runtime()

    print("\n=== N8 BENCH: Cache behavior ===")
    cache_result = bench_cache(n8_services)

    print("\n=== N8 BENCH: Endpoint routing ===")
    endpoint_results = bench_endpoints(app, n8_services)

    output = {
        "metadata": {
            "module": "N8 - Orchestrator",
            "date": date_str,
            "mode": "mocked_downstream_modules",
        },
        "cache": cache_result,
        "endpoints": endpoint_results,
    }

    json_path = BASE_DIR / "bench_n8_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[saved] {json_path}")

    md_path = BASE_DIR / "bench_n8.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_build_markdown(output, date_str))
    print(f"[saved] {md_path}")

    if CACHE_ROOT.exists():
        shutil.rmtree(CACHE_ROOT)

    passed = sum(1 for item in endpoint_results if item["status"] == "PASS")
    print(f"\n=== SUMMARY: cache={cache_result['status']} endpoints={passed}/{len(endpoint_results)} PASS ===")


if __name__ == "__main__":
    main()
