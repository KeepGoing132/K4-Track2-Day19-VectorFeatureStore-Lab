"""Regression checks for tenant isolation in the bonus memory agent."""
import json
import os
import subprocess
import sys

import pytest

from bonus import agent as module


@pytest.fixture
def memory_agent(monkeypatch):
    # Keep tests offline; exercise real Qdrant filtering with cheap vectors.
    monkeypatch.setattr(module, "_HAS_FASTEMBED", False)
    agent = module.HybridMemoryAgent(feature_store=module.MockFeastOnlineStore())
    yield agent
    if agent.qdrant is not None:
        agent.qdrant.close()


def test_recall_never_returns_another_users_memory(memory_agent):
    memory_agent.remember("Kubernetes PRIVATE_A", "u_001")
    memory_agent.remember("Kubernetes PRIVATE_B", "u_002")
    context = memory_agent.recall("Kubernetes", "u_001")
    assert "PRIVATE_A" in context
    assert "PRIVATE_B" not in context


def test_vector_filter_applies_before_top_k(memory_agent):
    memory_agent.remember("unrelated personal note", "u_001")
    for _ in range(12):
        memory_agent.remember("Kubernetes", "u_002")
    assert memory_agent._search_vector("Kubernetes", "u_001", top_k=1) == ["mem_0001"]


def test_unknown_profile_does_not_fall_back_to_another_user(memory_agent):
    profile = memory_agent.feast.get_online_features([{"user_id": "unknown"}])
    assert profile["user_id"] == "unknown"
    assert profile.get("topic_affinity") != "cloud_architecture"


def test_fallback_vectors_are_stable_across_processes():
    script = (
        "import json; from bonus.agent import FallbackEmbedder; "
        "print(json.dumps(FallbackEmbedder().embed(['Kubernetes tiếng Việt'])))"
    )
    results = []
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        results.append(json.loads(subprocess.check_output([sys.executable, "-c", script], env=env)))
    assert results[0] == results[1]


def test_real_feast_profile_and_rolling_query_window(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from feast import FeatureStore
    import pandas as pd
    from app.feast_repo.feature_views import user, user_profile_features, query_velocity_features
    from bonus import feature_store

    (tmp_path / "feature_store.yaml").write_text(
        "project: bonus_test\nprovider: local\nregistry: registry.db\n"
        "online_store:\n  type: sqlite\n  path: online_store.db\n"
        "offline_store:\n  type: file\nentity_key_serialization_version: 3\n",
        encoding="utf-8",
    )
    store = FeatureStore(repo_path=str(tmp_path))
    store.apply([user, user_profile_features, query_velocity_features])
    store.write_to_online_store("user_profile_features", pd.DataFrame([{
        "user_id": "u_001", "reading_speed_wpm": 187,
        "preferred_language": "vi", "topic_affinity": "cloud",
        "event_timestamp": datetime.now(timezone.utc),
    }]))
    adapter = feature_store.FeastOnlineStore(store)
    clock = [0.0]
    monkeypatch.setattr(feature_store.time, "monotonic", lambda: clock[0])
    adapter.record_query("u_001")
    clock[0] = 1800
    adapter.record_query("u_001")
    profile = adapter.get_online_features([{"user_id": "u_001"}])
    assert profile["reading_speed_wpm"] == 187
    assert profile["preferred_lang"] == "vi"
    assert profile["queries_last_hour"] == 2
    clock[0] = 3600
    adapter.record_query("u_001")
    assert adapter.get_online_features([{"user_id": "u_001"}])["queries_last_hour"] == 2
    unknown = adapter.get_online_features([{"user_id": "unknown"}])
    assert unknown["user_id"] == "unknown"
    assert unknown["topic_affinity"] == "unknown"
